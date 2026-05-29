from dataclasses import dataclass
from typing import Literal

import httpx

JudgeVerdict = Literal["AC", "WA", "RE", "TLE", "MLE", "CE"]

PAIZA_BASE_URL = "https://api.paiza.io"
PAIZA_API_KEY = "guest"
OUTPUT_PREVIEW_LIMIT = 4096


@dataclass(frozen=True)
class JudgeCaseInput:
    input: str
    expected_output: str


@dataclass(frozen=True)
class JudgeCaseOutput:
    verdict: JudgeVerdict
    time_ms: int | None
    memory_kb: int | None
    stdout_preview: str | None
    stderr_preview: str | None
    build_stderr_preview: str | None
    exit_code: int | None


@dataclass(frozen=True)
class JudgeOutput:
    verdict: JudgeVerdict
    total_time_ms: int | None
    peak_memory_kb: int | None
    cases: list[JudgeCaseOutput]


async def judge_with_paiza(
    *,
    source_code: str,
    language: str,
    cases: list[JudgeCaseInput],
    time_limit_ms: int,
    memory_limit_kb: int,
) -> JudgeOutput:
    outputs: list[JudgeCaseOutput] = []

    async with httpx.AsyncClient(timeout=40.0) as client:
        for case in cases:
            outputs.append(
                await _run_case(
                    client=client,
                    source_code=source_code,
                    language=language,
                    case=case,
                    time_limit_ms=time_limit_ms,
                    memory_limit_kb=memory_limit_kb,
                )
            )

    verdict = next((case.verdict for case in outputs if case.verdict != "AC"), "AC")
    total_time_ms = (
        sum(case.time_ms for case in outputs if case.time_ms is not None)
        if any(case.time_ms is not None for case in outputs)
        else None
    )
    peak_memory_kb = max(
        (case.memory_kb for case in outputs if case.memory_kb is not None),
        default=None,
    )

    return JudgeOutput(
        verdict=verdict,
        total_time_ms=total_time_ms,
        peak_memory_kb=peak_memory_kb,
        cases=outputs,
    )


async def _run_case(
    *,
    client: httpx.AsyncClient,
    source_code: str,
    language: str,
    case: JudgeCaseInput,
    time_limit_ms: int,
    memory_limit_kb: int,
) -> JudgeCaseOutput:
    try:
        session = await _create_session(
            client=client,
            source_code=source_code,
            language=language,
            input_text=case.input,
        )
        session_id = session["id"]
        completed = await _wait_for_completion(client=client, session_id=session_id)
        if not completed:
            return JudgeCaseOutput(
                verdict="TLE",
                time_ms=None,
                memory_kb=None,
                stdout_preview=None,
                stderr_preview=None,
                build_stderr_preview=None,
                exit_code=None,
            )

        details = await _get_details(client=client, session_id=session_id)
    except Exception as exc:
        return JudgeCaseOutput(
            verdict="RE",
            time_ms=None,
            memory_kb=None,
            stdout_preview=None,
            stderr_preview=_preview(str(exc)),
            build_stderr_preview=None,
            exit_code=None,
        )

    time_ms = _seconds_to_ms(details.get("time"))
    memory_kb = _bytes_to_kb(details.get("memory"))
    exit_code = _int_or_none(details.get("exit_code"))
    verdict = _verdict_for_details(
        details=details,
        actual_output=details.get("stdout"),
        expected_output=case.expected_output,
        time_ms=time_ms,
        memory_kb=memory_kb,
        exit_code=exit_code,
        time_limit_ms=time_limit_ms,
        memory_limit_kb=memory_limit_kb,
    )

    return JudgeCaseOutput(
        verdict=verdict,
        time_ms=time_ms,
        memory_kb=memory_kb,
        stdout_preview=_preview(details.get("stdout")),
        stderr_preview=_preview(details.get("stderr")),
        build_stderr_preview=_preview(details.get("build_stderr")),
        exit_code=exit_code,
    )


async def _create_session(
    *,
    client: httpx.AsyncClient,
    source_code: str,
    language: str,
    input_text: str,
) -> dict:
    response = await client.post(
        f"{PAIZA_BASE_URL}/runners/create.json",
        data={
            "api_key": PAIZA_API_KEY,
            "source_code": source_code,
            "language": language,
            "input": input_text,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError(data["error"])
    return data


async def _wait_for_completion(
    *,
    client: httpx.AsyncClient,
    session_id: str,
    max_polls: int = 30,
) -> bool:
    for _ in range(max_polls):
        await _sleep_one_second()
        response = await client.get(
            f"{PAIZA_BASE_URL}/runners/get_status.json",
            params={"api_key": PAIZA_API_KEY, "id": session_id},
        )
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise RuntimeError(data["error"])
        if data.get("status") == "completed":
            return True
    return False


async def _sleep_one_second() -> None:
    import asyncio

    await asyncio.sleep(1)


async def _get_details(*, client: httpx.AsyncClient, session_id: str) -> dict:
    response = await client.get(
        f"{PAIZA_BASE_URL}/runners/get_details.json",
        params={"api_key": PAIZA_API_KEY, "id": session_id},
    )
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError(data["error"])
    return data


def _verdict_for_details(
    *,
    details: dict,
    actual_output: str | None,
    expected_output: str,
    time_ms: int | None,
    memory_kb: int | None,
    exit_code: int | None,
    time_limit_ms: int,
    memory_limit_kb: int,
) -> JudgeVerdict:
    build_result = details.get("build_result")
    result = details.get("result")

    if build_result in {"failure", "error"}:
        return "CE"
    if memory_kb is not None and memory_limit_kb > 0 and memory_kb > memory_limit_kb:
        return "MLE"
    if result == "timeout" or (
        time_ms is not None and time_limit_ms > 0 and time_ms > time_limit_ms
    ):
        return "TLE"
    if result in {"failure", "error"} or (exit_code is not None and exit_code != 0):
        return "RE"
    if not compare_output(actual_output, expected_output):
        return "WA"
    return "AC"


def compare_output(actual: str | None, expected: str) -> bool:
    if actual is None:
        return False

    actual_lines = [
        line.rstrip() for line in actual.replace("\r\n", "\n").strip().split("\n")
    ]
    expected_lines = [
        line.rstrip() for line in expected.replace("\r\n", "\n").strip().split("\n")
    ]

    while actual_lines and actual_lines[-1] == "":
        actual_lines.pop()
    while expected_lines and expected_lines[-1] == "":
        expected_lines.pop()

    return actual_lines == expected_lines


def _seconds_to_ms(value: object) -> int | None:
    if value is None:
        return None
    return round(float(value) * 1000)


def _bytes_to_kb(value: object) -> int | None:
    if value is None:
        return None
    return round(float(value) / 1024)


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _preview(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text[:OUTPUT_PREVIEW_LIMIT]
