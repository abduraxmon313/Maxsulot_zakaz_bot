"""Super Admin bot FSM holatlari."""
from aiogram.fsm.state import State, StatesGroup


class EditSetting(StatesGroup):
    value = State()


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


class ShopLocation(StatesGroup):
    """Do'kon lokatsiyasini o'rnatish: lokatsiya + izoh."""
    location = State()
    comment = State()


class AddAdminRole(StatesGroup):
    """Yangi admin/superadmin qo'shish — telegram_id kutiladi."""
    telegram_id = State()
