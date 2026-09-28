from __future__ import annotations

import torch


class CTCAlignmentService:
    """
    CTC forced alignment for phoneme-level timestamps.

    The recognizer first obtains the phoneme sequence using greedy
    CTC decoding. This service then aligns that sequence against
    the original frame-level logits.

    Each phoneme receives:
    - start time
    - end time
    - duration
    - confidence

    The confidence represents the model's confidence in the
    recognized phoneme at its Viterbi center frame.
    It is NOT a direct pronunciation correctness score.
    """

    def __init__(self, processor):
        self.processor = processor

        self.blank_id = processor.tokenizer.pad_token_id

        if self.blank_id is None:
            raise RuntimeError(
                "Could not determine CTC blank token."
            )

    # =========================================================
    # Token helpers
    # =========================================================

    def _phoneme_to_id(self, phoneme: str) -> int:
        token_id = (
            self.processor.tokenizer
            .convert_tokens_to_ids(phoneme)
        )

        if token_id is None:
            raise ValueError(
                f"Unknown phoneme token: {phoneme}"
            )

        return int(token_id)

    # =========================================================
    # CTC state helpers
    # =========================================================

    def _build_extended_sequence(
        self,
        target_ids: list[int],
    ) -> list[int]:

        extended = [self.blank_id]

        for token_id in target_ids:
            extended.append(token_id)
            extended.append(self.blank_id)

        return extended

    def _allowed_previous_states(
        self,
        state_index: int,
        extended: list[int],
    ) -> list[int]:

        states = [state_index]

        if state_index > 0:
            states.append(state_index - 1)

        if state_index > 1:

            current_token = extended[state_index]
            previous_token = extended[state_index - 2]

            # CTC skip transition.
            #
            # We cannot jump directly between identical
            # consecutive phonemes.
            if (
                current_token != self.blank_id
                and current_token != previous_token
            ):
                states.append(state_index - 2)

        return states

    # =========================================================
    # Viterbi alignment
    # =========================================================

    def _viterbi(
        self,
        logits: torch.Tensor,
        target_ids: list[int],
    ) -> list[int] | None:

        if logits.ndim != 2:
            raise ValueError(
                "Expected logits with shape "
                "[frames, vocabulary]."
            )

        num_frames = logits.shape[0]

        if num_frames == 0:
            return None

        extended = self._build_extended_sequence(
            target_ids
        )

        num_states = len(extended)

        # -----------------------------------------------------
        # CTC feasibility
        # -----------------------------------------------------

        minimum_frames = len(target_ids)

        for i in range(1, len(target_ids)):

            if target_ids[i] == target_ids[i - 1]:
                minimum_frames += 1

        if num_frames < minimum_frames:
            return None

        # -----------------------------------------------------
        # Log probabilities
        # -----------------------------------------------------

        log_probs = torch.log_softmax(
            logits,
            dim=-1,
        )

        neg_inf = float("-inf")

        scores = torch.full(
            (num_frames, num_states),
            neg_inf,
            dtype=log_probs.dtype,
            device=log_probs.device,
        )

        backpointers = torch.full(
            (num_frames, num_states),
            -1,
            dtype=torch.long,
            device=log_probs.device,
        )

        # -----------------------------------------------------
        # Initial states
        # -----------------------------------------------------

        scores[0, 0] = log_probs[
            0,
            self.blank_id,
        ]

        if num_states > 1:
            scores[0, 1] = log_probs[
                0,
                extended[1],
            ]

        # -----------------------------------------------------
        # Dynamic programming
        # -----------------------------------------------------

        for frame_index in range(1, num_frames):

            for state_index in range(num_states):

                token_id = extended[state_index]

                previous_states = (
                    self._allowed_previous_states(
                        state_index,
                        extended,
                    )
                )

                best_score = neg_inf
                best_previous_state = -1

                for previous_state in previous_states:

                    candidate = scores[
                        frame_index - 1,
                        previous_state,
                    ]

                    if candidate > best_score:
                        best_score = candidate
                        best_previous_state = previous_state

                if best_previous_state < 0:
                    continue

                scores[
                    frame_index,
                    state_index,
                ] = (
                    best_score
                    + log_probs[
                        frame_index,
                        token_id,
                    ]
                )

                backpointers[
                    frame_index,
                    state_index,
                ] = best_previous_state

        # -----------------------------------------------------
        # Final state
        # -----------------------------------------------------

        last_blank = num_states - 1
        last_phoneme = num_states - 2

        if (
            scores[-1, last_phoneme]
            >= scores[-1, last_blank]
        ):
            state = last_phoneme
        else:
            state = last_blank

        if not torch.isfinite(
            scores[-1, state]
        ):
            return None

        # -----------------------------------------------------
        # Backtracking
        # -----------------------------------------------------

        path = [state]

        for frame_index in range(
            num_frames - 1,
            0,
            -1,
        ):

            previous_state = backpointers[
                frame_index,
                state,
            ].item()

            if previous_state < 0:
                return None

            state = previous_state

            path.append(state)

        path.reverse()

        if len(path) != num_frames:
            return None

        return path

    # =========================================================
    # Extract phoneme centers
    # =========================================================

    def _extract_phoneme_centers(
        self,
        state_path: list[int],
        phoneme_count: int,
    ) -> list[float | None]:

        centers = []

        for phoneme_index in range(
            phoneme_count
        ):

            state_index = (
                2 * phoneme_index + 1
            )

            frames = [
                frame_index
                for frame_index, state in enumerate(
                    state_path
                )
                if state == state_index
            ]

            if not frames:
                centers.append(None)
                continue

            # Use the center of the complete Viterbi region.
            center = (
                min(frames) + max(frames)
            ) / 2.0

            centers.append(center)

        return centers

    # =========================================================
    # Convert centers into temporal boundaries
    # =========================================================

    def _centers_to_boundaries(
        self,
        centers: list[float | None],
        num_frames: int,
    ) -> list[dict | None]:

        valid = [
            (index, center)
            for index, center in enumerate(centers)
            if center is not None
        ]

        if not valid:
            return [None] * len(centers)

        boundaries = [
            None
            for _ in centers
        ]

        for position, (
            phoneme_index,
            center,
        ) in enumerate(valid):

            # -------------------------------------------------
            # Start boundary
            # -------------------------------------------------

            if position == 0:

                if len(valid) > 1:

                    next_center = valid[
                        position + 1
                    ][1]

                    start = center - (
                        next_center - center
                    ) / 2.0

                else:
                    start = center - 1.0

            else:

                previous_center = valid[
                    position - 1
                ][1]

                start = (
                    previous_center + center
                ) / 2.0

            # -------------------------------------------------
            # End boundary
            # -------------------------------------------------

            if position == len(valid) - 1:

                if position > 0:

                    previous_center = valid[
                        position - 1
                    ][1]

                    end = center + (
                        center - previous_center
                    ) / 2.0

                else:
                    end = center + 1.0

            else:

                next_center = valid[
                    position + 1
                ][1]

                end = (
                    center + next_center
                ) / 2.0

            # -------------------------------------------------
            # Clamp
            # -------------------------------------------------

            start = max(
                0.0,
                min(
                    float(start),
                    num_frames - 1,
                ),
            )

            end = max(
                start,
                min(
                    float(end),
                    num_frames,
                ),
            )

            boundaries[
                phoneme_index
            ] = {
                "start_frame": start,
                "end_frame": end,
            }

        return boundaries

    # =========================================================
    # Public API
    # =========================================================

    def align(
        self,
        logits: torch.Tensor,
        phonemes: list[str],
        duration: float,
        frame_confidences=None,
    ) -> list[dict]:

        if not phonemes:
            return []

        if duration <= 0:
            return [
                {
                    "phoneme": phoneme,
                    "start": None,
                    "end": None,
                    "duration": None,
                    "confidence": None,
                }
                for phoneme in phonemes
            ]

        if logits.ndim != 3:
            raise ValueError(
                "Expected logits with shape "
                "[batch, frames, vocabulary]."
            )

        if logits.shape[0] < 1:
            return []

        # -----------------------------------------------------
        # First batch item
        # -----------------------------------------------------

        logits = logits[0]

        num_frames = logits.shape[0]

        if num_frames == 0:
            return []

        # -----------------------------------------------------
        # Phoneme IDs
        # -----------------------------------------------------

        target_ids = [
            self._phoneme_to_id(
                phoneme
            )
            for phoneme in phonemes
        ]

        # -----------------------------------------------------
        # Viterbi
        # -----------------------------------------------------

        state_path = self._viterbi(
            logits=logits,
            target_ids=target_ids,
        )

        if state_path is None:

            return [
                {
                    "phoneme": phoneme,
                    "start": None,
                    "end": None,
                    "duration": None,
                    "confidence": None,
                }
                for phoneme in phonemes
            ]

        # -----------------------------------------------------
        # Phoneme centers
        # -----------------------------------------------------

        centers = self._extract_phoneme_centers(
            state_path=state_path,
            phoneme_count=len(phonemes),
        )

        # -----------------------------------------------------
        # Convert centers to boundaries
        # -----------------------------------------------------

        boundaries = self._centers_to_boundaries(
            centers=centers,
            num_frames=num_frames,
        )

        # -----------------------------------------------------
        # Frame -> seconds
        # -----------------------------------------------------

        frame_duration = (
            duration / num_frames
        )

        results = []

        for phoneme_index, (
            phoneme,
            boundary,
        ) in enumerate(
            zip(
                phonemes,
                boundaries,
            )
        ):

            if boundary is None:

                results.append(
                    {
                        "phoneme": phoneme,
                        "start": None,
                        "end": None,
                        "duration": None,
                        "confidence": None,
                    }
                )

                continue

            start = (
                boundary["start_frame"]
                * frame_duration
            )

            end = (
                boundary["end_frame"]
                * frame_duration
            )

            # -------------------------------------------------
            # Numerical safety
            # -------------------------------------------------

            start = max(
                0.0,
                min(start, duration),
            )

            end = max(
                start,
                min(end, duration),
            )

            # -------------------------------------------------
            # Phoneme confidence
            # -------------------------------------------------

            confidence = None

            center = centers[phoneme_index]

            if (
                frame_confidences is not None
                and center is not None
            ):

                center_frame = int(
                    round(center)
                )

                if (
                    0 <= center_frame
                    < len(frame_confidences)
                ):

                    confidence = float(
                        frame_confidences[
                            center_frame
                        ]
                    )

                    # Numerical safety.
                    confidence = max(
                        0.0,
                        min(
                            confidence,
                            1.0,
                        )
                    )

                    confidence = round(
                        confidence,
                        3,
                    )

            # -------------------------------------------------
            # Final result
            # -------------------------------------------------

            results.append(
                {
                    "phoneme": phoneme,
                    "start": round(
                        start,
                        3,
                    ),
                    "end": round(
                        end,
                        3,
                    ),
                    "duration": round(
                        end - start,
                        3,
                    ),
                    "confidence": confidence,
                }
            )

        return results