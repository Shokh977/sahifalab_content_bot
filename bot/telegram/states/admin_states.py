from aiogram.fsm.state import State, StatesGroup


class AddSourceStates(StatesGroup):
    waiting_name = State()
    waiting_url = State()
    waiting_kind = State()
    waiting_pillar = State()


class AddTopicStates(StatesGroup):
    waiting_theme = State()
    waiting_notes = State()


class AddQuoteStates(StatesGroup):
    waiting_quote_text = State()
    waiting_author = State()
    waiting_translation = State()
    waiting_source_note = State()


class AddFactStates(StatesGroup):
    waiting_category = State()
    waiting_fact_text = State()
    waiting_source = State()


class AddPollStates(StatesGroup):
    waiting_question = State()
    waiting_options = State()


class EditDraftStates(StatesGroup):
    waiting_new_text = State()


class ScheduleDraftStates(StatesGroup):
    waiting_custom_datetime = State()
