"""Sotuv bot FSM holatlari."""
from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    phone = State()
