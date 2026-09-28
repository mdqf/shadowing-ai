from app.services.pronunciation_analysis_v2 import (
    PronunciationAnalysisV2,
)


service = PronunciationAnalysisV2()


alignment_result = {
    "alignment": [
        {
            "expected": "hh",
            "actual": "hh",
            "status": "match",
            "expected_confidence": 1.0,
            "actual_confidence": 0.98,
        },
        {
            "expected": "eh",
            "actual": "ah",
            "status": "substitution",
            "expected_confidence": 0.996,
            "actual_confidence": 0.791,
        },
        {
            "expected": "l",
            "actual": "l",
            "status": "match",
            "expected_confidence": 1.0,
            "actual_confidence": 0.99,
        },
        {
            "expected": "p",
            "actual": "b",
            "status": "substitution",
            "expected_confidence": 0.99,
            "actual_confidence": 0.95,
        },
        {
            "expected": "r",
            "actual": "r",
            "status": "match",
            "expected_confidence": 0.543,
            "actual_confidence": 0.93,
        },
    ]
}


evidence_result = {
    "items": [
        {
            "evidence_status": "confirmed_match",
            "confidence_level": "high",
            "likely_error": False,
            "reason": "Phonemes match with sufficient confidence.",
        },
        {
            "evidence_status": "possible_error",
            "confidence_level": "medium",
            "likely_error": False,
            "reason": "Further evidence is needed to strongly confirm the error.",
        },
        {
            "evidence_status": "confirmed_match",
            "confidence_level": "high",
            "likely_error": False,
            "reason": "Phonemes match with sufficient confidence.",
        },
        {
            "evidence_status": "possible_error",
            "confidence_level": "high",
            "likely_error": True,
            "reason": "The phonemes differ and recognition confidence is high.",
        },
        {
            "evidence_status": "uncertain",
            "confidence_level": "low",
            "likely_error": False,
            "reason": "Recognition confidence is too low.",
        },
    ]
}


result = service.analyze(
    alignment_result=alignment_result,
    evidence_result=evidence_result,
)


for item in result["items"]:
    print(
        f'{item.get("expected")} -> '
        f'{item.get("actual")}'
    )

    print(
        "Status:",
        item.get("status")
    )

    print(
        "Evidence:",
        item.get("evidence_status")
    )

    print(
        "Similarity:",
        item.get("phonetic_similarity")
    )

    print(
        "Error type:",
        item.get("error_type")
    )

    print(
        "Severity:",
        item.get("severity")
    )

    print(
        "Severity score:",
        item.get("severity_score")
    )

    print("-" * 70)


print("\nSUMMARY")
print(result["summary"])