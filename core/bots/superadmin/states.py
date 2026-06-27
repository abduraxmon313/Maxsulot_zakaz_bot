"""Super Admin bot FSM holatlari."""
from aiogram.fsm.state import State, StatesGroup


class EditSetting(StatesGroup):
    value = State()
