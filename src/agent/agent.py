import re
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
from src.tools import TOOL_REGISTRY, execute_tool, get_tool_descriptions


class ReActAgent:
    """
    ReAct-style Agent v2: Thought-Action-Observation loop with
    improved prompt engineering, metrics tracking, and error recovery.
    """

    def __init__(self, llm: LLMProvider, tools: Optional[List[Dict[str, Any]]] = None, max_steps: int = 10):
        self.llm = llm
        self.tools = tools if tools is not None else TOOL_REGISTRY
        self.max_steps = max_steps
        self.history = []
        self.version = "v2"

    def get_system_prompt(self) -> str:
        """
        v2 system prompt: stricter format, few-shot travel example,
        explicit error-handling instructions.
        """
        tool_descriptions = get_tool_descriptions()
        return f"""You are Voyanta, a smart travel-planning agent for Vietnam destinations.
You ONLY help with travel planning in Vietnam. You do NOT answer questions outside of travel.
IMPORTANT: Always respond in Vietnamese. Your Final Answer MUST be in Vietnamese.

## Domain Guardrails (MANDATORY):
- You are ONLY a travel planner. Do NOT answer questions about cars, shopping, technology, politics, or any non-travel topic.
- If the user asks about something NOT related to travel (e.g. "mua xe VinFast", "giá iPhone"), respond IMMEDIATELY with:
  Thought: Câu hỏi này không liên quan đến du lịch.
  Final Answer: Xin lỗi, tôi chỉ hỗ trợ lập kế hoạch du lịch Việt Nam. Bạn có thể hỏi tôi về điểm đến, khách sạn, ẩm thực, thời tiết, ngân sách chuyến đi. Bạn muốn đi đâu?
- If the user uses rude or offensive language, respond IMMEDIATELY with:
  Thought: Người dùng sử dụng ngôn từ không phù hợp.
  Final Answer: Xin vui lòng sử dụng ngôn ngữ lịch sự. Tôi sẵn sàng giúp bạn lập kế hoạch du lịch Việt Nam! Bạn muốn khám phá Đà Nẵng, Phú Quốc, Hội An, Nha Trang hay Sa Pa?
- Do NOT try to use any tools for off-topic requests. Go directly to Final Answer.

## Available Tools:
{tool_descriptions}

## STRICT Output Format — follow EXACTLY every turn:

Thought: <your reasoning about what info you still need>
Action: tool_name(arg1, arg2, ...)

Then STOP and wait for the Observation.

When you have gathered enough information:
Thought: I have all the information needed to answer.
Final Answer: <your complete, well-formatted answer>

## Rules:
- Call ONE tool per turn. Never chain multiple Actions.
- Only use tool names listed above. Do NOT invent tools.
- Separate arguments with commas inside parentheses.
- If a tool returns an error, read the error message and adjust your arguments.
- Always end with a Final Answer.
- If the user does NOT specify a city, suggest popular options (Da Nang, Phu Quoc, Hoi An, Nha Trang, Sapa) in your Final Answer instead of guessing.
- If the user asks to COMPARE two destinations, look up both cities separately then compare in your Final Answer.
- If a tool says "No data found", inform the user and suggest an alternative city that does have data.

## Few-shot Example:

User: "I want to go to Da Nang for 3 days, budget 5 million VND, I like beach."

Thought: First I should look up destination information for Da Nang.
Action: search_destination(Da Nang)

Observation: Da Nang is in central vietnam. Highlights: my khe beach, ba na hills, dragon bridge. Best season: march to august. Local food: mi quang, banh xeo, seafood.

Thought: The user likes beach, let me find beach attractions in Da Nang.
Action: search_attraction(Da Nang, beach)

Observation: Top attractions in Da Nang for beach: 1. My Khe Beach (free) 2. Ba Na Hills (~900000 VND) 3. Cham Islands tour (~500000 VND)

Thought: Now let me estimate hotel cost. Budget is limited so 3-star for 3 nights.
Action: get_hotel_price(Da Nang, 3, 3)

Observation: Hotel 3-star in Da Nang: ~500,000 VND/night. 3 nights total: 1,500,000 VND.

Thought: Let me estimate food cost at mid level for 3 days.
Action: estimate_food_cost(Da Nang, 3, mid)

Observation: Food cost (mid) in Da Nang: ~300,000 VND/day. 3 days total: 900,000 VND.

Thought: Total so far: hotel 1,500,000 + food 900,000 + attractions ~1,400,000 = 3,800,000. Let me check budget.
Action: check_budget(3800000, 5000000)

Observation: Total: 3,800,000 VND. Budget: 5,000,000 VND. Remaining: 1,200,000 VND.

Thought: I have all the information needed to answer.
Final Answer: Here is your 3-day Da Nang trip plan with a 5,000,000 VND budget:

**Accommodation**: 3-star hotel — 1,500,000 VND (3 nights × 500,000)
**Food**: Mid-range — 900,000 VND (3 days × 300,000)
**Attractions**: ~1,400,000 VND
  1. My Khe Beach (free)
  2. Ba Na Hills (900,000 VND)
  3. Cham Islands tour (500,000 VND)

**Total**: 3,800,000 VND — you have 1,200,000 VND remaining for transport and extras!
"""

    @staticmethod
    def _extract_final_answer(text: str) -> Optional[str]:
        """Extract Final Answer from LLM output."""
        match = re.search(r"Final\s*Answer\s*:\s*(.*)", text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            answer = match.group(1).strip()
            # Cut off if LLM starts a new Thought after the answer
            answer = re.split(r"\nThought:", answer)[0].strip()
            if answer:
                return answer
        return None

    @staticmethod
    def _extract_action(text: str) -> Optional[Dict[str, str]]:
        """Parse Action: tool_name(args) from LLM output."""
        # Pattern 1: Action: tool_name(args)
        match = re.search(
            r"Action\s*:\s*([a-zA-Z_][\w]*)\s*\((.*?)\)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match:
            return {
                "tool_name": match.group(1).strip(),
                "args": match.group(2).strip(),
            }

        # Pattern 2: Action: tool_name with JSON
        match = re.search(r"Action\s*:\s*(\w+)\s*(\{.*?\})", text, re.IGNORECASE | re.DOTALL)
        if match:
            return {
                "tool_name": match.group(1).strip(),
                "args": match.group(2).strip(),
            }

        return None

    def run(self, user_input: str) -> Dict[str, Any]:
        """
        Execute the ReAct loop. Returns a dict with:
        - answer: final answer string
        - steps: number of steps taken
        - traces: list of step traces for debugging
        - status: 'success' | 'max_steps_reached' | 'error'
        """
        logger.log_event("AGENT_START", {
            "input": user_input,
            "model": self.llm.model_name,
            "version": self.version,
            "max_steps": self.max_steps,
        })

        current_prompt = f"User Question: {user_input}"
        system_prompt = self.get_system_prompt()
        steps = 0
        last_response = ""
        traces = []

        while steps < self.max_steps:
            steps += 1

            # Generate LLM response
            try:
                result = self.llm.generate(current_prompt, system_prompt=system_prompt)
            except Exception as exc:
                logger.log_event("LLM_ERROR", {"step": steps, "error": str(exc)})
                return {
                    "answer": f"LLM error at step {steps}: {exc}",
                    "steps": steps,
                    "traces": traces,
                    "status": "error",
                }

            content = result.get("content", "").strip()
            usage = result.get("usage", {})
            latency_ms = result.get("latency_ms", 0)
            provider = result.get("provider", "unknown")
            last_response = content

            # Track metrics
            tracker.track_request(provider, self.llm.model_name, usage, latency_ms)

            step_trace = {
                "step": steps,
                "thought": "",
                "action": None,
                "observation": None,
                "llm_output": content,
                "usage": usage,
                "latency_ms": latency_ms,
            }

            logger.log_event("AGENT_STEP", {
                "step": steps,
                "response": content[:300],
                "usage": usage,
                "latency_ms": latency_ms,
            })

            # Extract Thought for trace
            thought_match = re.search(r"Thought\s*:\s*(.*?)(?=Action|Final\s*Answer|$)", content, re.DOTALL | re.IGNORECASE)
            if thought_match:
                step_trace["thought"] = thought_match.group(1).strip()

            # Check Final Answer first
            final_answer = self._extract_final_answer(content)
            if final_answer:
                step_trace["action"] = "Final Answer"
                traces.append(step_trace)
                logger.log_event("AGENT_END", {"steps": steps, "status": "success"})

                run_result = {
                    "answer": final_answer,
                    "steps": steps,
                    "traces": traces,
                    "status": "success",
                }
                self.history.append({"input": user_input, **run_result})
                return run_result

            # Parse Action
            action = self._extract_action(content)
            if action:
                tool_name = action["tool_name"]
                tool_args = action["args"]

                observation = execute_tool(tool_name, tool_args)

                logger.log_event("AGENT_TOOL_CALL", {
                    "step": steps,
                    "tool": tool_name,
                    "args": tool_args,
                    "observation": observation,
                })

                step_trace["action"] = f"{tool_name}({tool_args})"
                step_trace["observation"] = observation
                traces.append(step_trace)

                current_prompt += (
                    f"\n\nAssistant Output:\n{content}"
                    f"\nObservation: {observation}"
                    "\nContinue with Thought/Action or provide Final Answer."
                )
            else:
                # No valid Action or Final Answer — nudge LLM
                logger.log_event("PARSE_ERROR", {
                    "step": steps,
                    "content": content[:300],
                })

                step_trace["action"] = "PARSE_ERROR"
                step_trace["observation"] = "Format not recognized"
                traces.append(step_trace)

                current_prompt += (
                    f"\n\nAssistant Output:\n{content}"
                    "\nObservation: I could not parse your output. "
                    "Please use exactly: Action: tool_name(arg1, arg2) "
                    "or Final Answer: your answer."
                )

        # Max steps reached
        logger.log_event("AGENT_END", {"steps": steps, "status": "max_steps_reached"})
        return {
            "answer": f"Could not finish within {self.max_steps} steps. Last output:\n{last_response}",
            "steps": steps,
            "traces": traces,
            "status": "max_steps_reached",
        }

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """Legacy helper — delegates to registry."""
        return execute_tool(tool_name, args)
