"""Admin bot FSM holatlari."""
from aiogram.fsm.state import State, StatesGroup


class AddProduct(StatesGroup):
    name = State()
    price = State()
    stock = State()
    category = State()
    photo = State()


class AddCategory(StatesGroup):
    name = State()
    emoji = State()


class EditPrice(StatesGroup):
    value = State()


class EditStock(StatesGroup):
    value = State()
