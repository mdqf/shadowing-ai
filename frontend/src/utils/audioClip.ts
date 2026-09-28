// =========================================================
// Web Audio API Reference Clip Extractor
// =========================================================

export async function extractAudioClip(
  mediaSource: Blob | string,
  startTime: number,
  endTime: number,
  paddingSeconds = 0.3
): Promise<Blob> {
  const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)({
    sampleRate: 16000,
  });

  let arrayBuffer: ArrayBuffer;
  if (typeof mediaSource === "string") {
    const response = await fetch(mediaSource);
    arrayBuffer = await response.arrayBuffer();
  } else {
    arrayBuffer = await mediaSource.arrayBuffer();
  }

  const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
  const sampleRate = audioBuffer.sampleRate;

  // Subtitle timestamps aren't reliable audio boundaries (timed for
  // reading comfort, not precise speech onset/offset), so we grab a
  // slightly WIDER clip than the raw subtitle window. The backend's
  // VAD step then finds the true speech boundaries within this
  // padding, anchored on the original (un-padded) subtitle timing —
  // see reference_anchor_start/end below. 0.3s matches the value the
  // VAD anchoring logic was tuned and validated against.
  const paddedStart = Math.max(0, startTime - paddingSeconds);
  const paddedEnd = Math.min(audioBuffer.duration, endTime + paddingSeconds);

  const startSample = Math.floor(paddedStart * sampleRate);
  const endSample = Math.floor(paddedEnd * sampleRate);
  const frameCount = Math.max(0, endSample - startSample);

  if (frameCount === 0) {
    throw new Error("Invalid time range for audio clip extraction.");
  }

  const offlineCtx = new OfflineAudioContext(
    audioBuffer.numberOfChannels,
    frameCount,
    sampleRate
  );

  const source = offlineCtx.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(offlineCtx.destination);
  source.start(0, paddedStart, paddedEnd - paddedStart);

  const renderedBuffer = await offlineCtx.startRendering();
  return audioBufferToWavBlob(renderedBuffer);
}

function audioBufferToWavBlob(buffer: AudioBuffer): Blob {
  const numChannels = buffer.numberOfChannels;
  const sampleRate = buffer.sampleRate;
  const format = 1; // PCM
  const bitDepth = 16;
  const bytesPerSample = bitDepth / 8;
  const blockAlign = numChannels * bytesPerSample;
  const dataSize = buffer.length * blockAlign;
  const headerSize = 44;
  const totalSize = headerSize + dataSize;

  const arrayBuffer = new ArrayBuffer(totalSize);
  const dataView = new DataView(arrayBuffer);

  const writeString = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      dataView.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  writeString(0, "RIFF");
  dataView.setUint32(4, 36 + dataSize, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  dataView.setUint32(16, 16, true);
  dataView.setUint16(20, format, true);
  dataView.setUint16(22, numChannels, true);
  dataView.setUint32(24, sampleRate, true);
  dataView.setUint32(28, sampleRate * blockAlign, true);
  dataView.setUint16(32, blockAlign, true);
  dataView.setUint16(34, bitDepth, true);
  writeString(36, "data");
  dataView.setUint32(40, dataSize, true);

  let offset = 44;
  for (let i = 0; i < buffer.length; i++) {
    for (let channel = 0; channel < numChannels; channel++) {
      const sample = Math.max(-1, Math.min(1, buffer.getChannelData(channel)[i]));
      const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
      dataView.setInt16(offset, intSample, true);
      offset += 2;
    }
  }

  return new Blob([dataView], { type: "audio/wav" });
}