"""Admin bot FSM holatlari."""
from aiogram.fsm.state import State, StatesGroup


class CancelOrder(StatesGroup):
    """Buyurtmani bekor qilish/rad etish — sabab so'raladi."""
    reason = State()
