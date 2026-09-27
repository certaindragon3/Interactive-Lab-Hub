"""Application-owned check-in ledger. No model, audio or GPIO dependencies."""
import copy
import json
import os
import re
import tempfile
from pathlib import Path

RUBRIC = {"vegetable": 10, "fruit": 10, "protein": 5, "staple": 5,
          "dessert": -5, "fried": -10, "other": 0}
RUBRIC_VERSION = "menu-game-v1"


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".pending-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class Ledger:
    def __init__(self, path):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {
            "rubric": RUBRIC_VERSION, "entries": {}, "calls": {}, "closed": False}
        if self.data["rubric"] != RUBRIC_VERSION:
            raise ValueError("Unsupported saved rubric")
        self.save()

    def save(self):
        self.data["snapshot"] = self.snapshot()
        atomic_json(self.path, self.data)

    def snapshot(self):
        entries = list(self.data["entries"].values())
        known = [e for e in entries if e["portion"] is not None]
        totals = {category: sum(RUBRIC[category] for e in known if e["category"] == category)
                  for category in RUBRIC}
        contributions = {k: max(-20, min(20, v)) for k, v in totals.items()}
        return {"rubric": RUBRIC_VERSION, "score": max(0, min(100, 50 + sum(contributions.values()))) if known else None,
                "base": 50, "category_points": contributions, "entries": copy.deepcopy(entries),
                "pending_portions": sum(e["portion"] is None for e in entries),
                "scope": "this check-in only; fictional menu game, not nutrition or calories"}

    def execute(self, call_id, name, args):
        fingerprint = json.dumps([name, args], sort_keys=True, ensure_ascii=False)
        previous = self.data["calls"].get(call_id)
        if previous:
            if previous["fingerprint"] != fingerprint:
                return {"ok": False, "error": "call_id reused with different arguments"}
            return copy.deepcopy(previous["result"])
        before = copy.deepcopy(self.data)
        try:
            if name == "get_food_log":
                result = {"ok": True, **self.snapshot()}
            elif self.data["closed"]:
                result = {"ok": False, "error": "check-in is frozen"}
            elif name == "log_food":
                result = self._log(args)
            else:
                result = {"ok": False, "error": "unknown tool"}
            self.data["calls"][call_id] = {"fingerprint": fingerprint, "result": result}
            self.save()
            return result
        except (ValueError, TypeError, KeyError) as exc:
            self.data = before
            return {"ok": False, "error": str(exc)}
        except BaseException:
            self.data = before
            raise

    def _log(self, args):
        if not isinstance(args, dict):
            raise ValueError("arguments must be an object")
        entry_id = args.get("entry_id")
        action = args.get("action")
        if not isinstance(entry_id, str) or not entry_id or len(entry_id) > 50:
            raise ValueError("entry_id must be a stable short ID")
        entries = self.data["entries"]
        if action == "remove":
            if entry_id not in entries:
                raise ValueError("Unknown entry_id; inspect get_food_log first")
            del entries[entry_id]
        elif action in ("add", "correct"):
            food, portion, category = args.get("food"), args.get("portion"), args.get("category")
            if not isinstance(food, str) or not food.strip() or len(food) > 40:
                raise ValueError("food must have 1-40 characters")
            if portion is not None and (not isinstance(portion, str) or not portion.strip() or len(portion) > 30):
                raise ValueError("portion must be null (unknown) or 1-30 characters stated by user")
            if portion is not None:
                words = r"\b(?:a|an|half|one|two|three|four|five|six|seven|eight|nine|ten)\b"
                chinese_numbers = "零〇一二三四五六七八九十百千万两半"
                has_amount = any(c.isnumeric() or c in chinese_numbers for c in portion) or re.search(words, portion, re.I)
                remainder = re.sub(words, "", portion, flags=re.I)
                has_unit = any(c.isalpha() and not c.isnumeric() and c not in chinese_numbers for c in remainder)
                if not has_amount or not has_unit:
                    raise ValueError("Portion needs an explicit amount and unit; size alone is unknown. Use portion=null, never invent a quantity. Explicit number words may be normalized to digits in the user's language.")
            if category not in RUBRIC:
                raise ValueError("Unknown category")
            entry = {"entry_id": entry_id, "food": food.strip(), "portion": portion.strip() if portion else None,
                     "category": category}
            if action == "correct" and entry_id not in entries:
                raise ValueError("Unknown correction target; inspect get_food_log first")
            if action == "add" and entry_id in entries:
                if entries[entry_id] != entry:
                    raise ValueError("Existing ID: use correct, not add")
                return {"ok": True, "duplicate": True, **self.snapshot()}
            if action == "add" and any(all(e[k] == entry[k] for k in ("food", "portion", "category")) for e in entries.values()):
                if args.get("separate_serving") is not True:
                    raise ValueError("Possible duplicate; only use separate_serving for an explicitly additional serving")
            if action == "add" and len(entries) >= 12:
                raise ValueError("Demo check-in limit: 12 entries")
            entries[entry_id] = entry
        else:
            raise ValueError("action must be add, correct or remove")
        return {"ok": True, **self.snapshot()}

    def freeze(self, reconciled):
        self.data["closed"] = True
        self.data["reconciled"] = reconciled
        self.data["summary"] = self.summary(reconciled)
        self.save()
        return self.data["summary"]

    def summary_template(self, reconciled=True):
        state = self.snapshot()
        values = {f"[[FOOD_{i}]]": e["food"] for i, e in enumerate(state["entries"])}
        if state["score"] is not None:
            values["[[SCORE]]"] = state["score"]
        if state["pending_portions"]:
            values["[[PENDING]]"] = state["pending_portions"]
        return self.summary(reconciled, placeholders=True), values

    def summary(self, reconciled=True, placeholders=False):
        state = self.snapshot()
        foods = "；".join(e["food"] + "，" + (e["portion"] or "份量未确认") for e in state["entries"])
        names = [f"[[FOOD_{i}]]" if placeholders else e["food"] for i, e in enumerate(state["entries"])]
        text = ("、".join(names) + "——" if foods else "这次没有保存食物，")
        if state["score"] is None:
            text += "份量还没说清，分数先欠着。"
        else:
            text += ("[[SCORE]]" if placeholders else str(state["score"])) + "分。"
        if state["pending_portions"]:
            text += "还有" + ("[[PENDING]]" if placeholders else str(state["pending_portions"])) + "项没说份量，未计分。"
        if not reconciled:
            text += "最后那段没核对完，这里只算已保存的。"
        categories = {e["category"] for e in state["entries"]}
        produce = "蔬菜" if "vegetable" in categories else "水果"
        indulgence = "甜点和炸物" if {"dessert", "fried"} <= categories else "甜点" if "dessert" in categories else "炸物"
        if {"vegetable", "dessert", "fried"} <= categories:
            text += "蔬菜本来想拯救全场，结果被甜点和炸物架空了。散会，下次给它配点靠谱的队友！"
        elif categories & {"vegetable", "fruit"} and not categories & {"dessert", "fried"}:
            text += f"这回我先给你鼓掌，{produce}确实有戏份。继续保持，咱们下顿见！"
        elif categories & {"vegetable", "fruit"} and categories & {"dessert", "fried"}:
            text += f"{produce}刚想当主角，{indulgence}就带资进组了。行，今天先不拍续集，咱们下顿见！"
        elif categories & {"dessert", "fried"}:
            text += "这菜单的快乐部门经费真足。今天先到这儿，下次争取给其他部门也拨点款！"
        elif categories:
            text += "菜单我收下了，今天先放你下班。下顿见，别给我憋个大反转！"
        else:
            text += "看来今天是来试音的。下次带着菜单来，我的嘴可不白开工！"
        return text


TOOLS = [{"type": "function", "name": "get_food_log", "description": "Read authoritative saved entries, IDs, score and rubric before editing.",
          "parameters": {"type": "object", "properties": {}, "additionalProperties": False}, "strict": True},
         {"type": "function", "name": "log_food", "description": "Save one user-reported food, correct by existing ID, or remove. Never guess portions. Retries reuse IDs. No calorie estimates.",
          "strict": True, "parameters": {"type": "object", "additionalProperties": False,
          "properties": {"entry_id": {"type": "string"}, "action": {"type": "string", "enum": ["add", "correct", "remove"]},
                         "food": {"type": "string"}, "portion": {"type": ["string", "null"]},
                         "category": {"type": "string", "enum": list(RUBRIC)},
                         "separate_serving": {"type": "boolean"}},
          "required": ["entry_id", "action", "food", "portion", "category", "separate_serving"]}}]

BACKEND_PROMPT = """You maintain a spoken food check-in. The coach always speaks English. Store food names in English, faithfully translating user reports when necessary so the recap stays English. Preserve the user's stated portions; explicitly stated number words may be normalized to digits, but never infer a quantity. Read get_food_log at the start of a check-in, when an entry ID is uncertain, and during final reconciliation. Otherwise reuse the authoritative IDs and records already in tool results; do not reread the full log before every add. Log every food the user says they ate using log_food, including foods with unknown portions (portion=null). Never infer a portion. Ask ONE short clarification for missing portions. An explicit quantity like one bowl or half a slice is enough for this fictional game. This is not calorie counting. Categories: vegetable, fruit, protein, staple, dessert, fried, other; choose fried over protein for fried chicken, dessert for cake. Mixed/unclear dishes use other, never invent ingredient entries. Keep stable entry IDs. Corrections replace the original ID, not a new add. Repeated mentions/recaps are not additional meals. separate_serving=true only when user explicitly says they ate an additional serving. On final reconciliation inspect the conversation for unlogged food/corrections, apply them once, and finish. Never log hypothetical food, assistant jokes, or quoted examples as eaten. Tool errors mean not saved. Return a SHORT factual update for the voice actor: what changed, whether it saved, and any unresolved portion. Do not write a spoken acknowledgment, joke, recap, or instruction to say 已记录/已更正. The voice actor should converse naturally while you maintain the record. Include the authoritative score only when the user asks for it or at final reconciliation; never turn routine bookkeeping into dialogue. Never make up a score or calories. Humor targets food choices, never bodies or weight. Gentle tone on request."""
