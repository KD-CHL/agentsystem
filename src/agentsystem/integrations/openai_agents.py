from __future__ import annotations

from dataclasses import dataclass


class OpenAIAgentsSDKUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenAIAgentSpec:
    name: str
    instructions: str


def build_openai_agent(spec: OpenAIAgentSpec):
    """Build an OpenAI Agents SDK Agent when the optional extra is installed.

    The core MVP does not import the SDK at startup because private deployments
    often run fully offline or behind an internal model gateway. This adapter is
    the seam where production can map the local Agent definitions to real SDK
    agents, tools, handoffs, guardrails, and tracing.
    """

    try:
        from agents import Agent
    except ImportError as exc:
        raise OpenAIAgentsSDKUnavailable(
            "Install the optional OpenAI extra with: pip install -e '.[openai]'"
        ) from exc
    return Agent(name=spec.name, instructions=spec.instructions)
