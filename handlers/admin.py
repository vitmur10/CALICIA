from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from bot.api.swagger import SwaggerCRM
from bot.config import Config
from bot.db import Repo
from bot.filters.admin import AdminFilter, AdminInlineFilter
import bot.keyboards.admin as kb
from bot.structrures.callback_data import UserData

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.callback_query(F.data == 'admin')
@router.message(F.text == '/admin')
async def admin_panel(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    action = event.__getattribute__('answer') if event.__class__ == Message else event.message.__getattribute__('edit_text')

    await action("👑 <b>Адмін-панель</b>: ", reply_markup=kb.menu())


@router.inline_query(AdminInlineFilter())
async def users_inline(query: InlineQuery, repo: Repo):
    data = await repo.get_user_by_request(query.query.replace('user:', ''))
    results = [InlineQueryResultArticle(id=str(user.id),
                                        title=user.full_name + (", @" + user.username if user.username else "") + (
                                            f" {user.source_name} 🤝" if user.is_partner else ""), input_message_content=InputTextMessageContent(
            message_text=f"user:{user.id}", parse_mode="HTML")) for user in data] if data != [] else [
        InlineQueryResultArticle(id='0', title='Нічого не знайдено',
                                 input_message_content=InputTextMessageContent(message_text='_', parse_mode="HTML"))]
    await query.answer(results=results, cache_time=1, is_personal=True)


@router.message(F.text.startswith('user'))
async def user(message: Message, repo: Repo):
    user = await repo.get_user(int(message.text.replace('user:', '')))

    await message.answer(f"👤 <b>{user.full_name}</b>\n"
                         f"<b>» ID</b>:  {user.id}\n"
                         f"{f'<b>» Юзернейм</b>:  @{user.username}' if user.username else ''}", reply_markup=kb.user(user))


@router.callback_query(UserData.filter())
async def user_data(query: CallbackQuery, repo: Repo, config: Config, bot: Bot, swagger: SwaggerCRM, state: FSMContext, callback_data: UserData):
    user = await repo.get_user(callback_data.id)
    state_data = await state.get_data()

    if callback_data.action:
        if callback_data.action == 'promote':
            sources = await swagger.get_request('/order/source', limit=50)
            sources = {source['id']: source['name'] for source in sources['data'] if source['name'].startswith('посередник')}
            await state.update_data(sources=sources)

            await query.message.edit_text('🌀 <b>Оберіть джерело</b>: ', reply_markup=kb.sources_list(user, sources))
            return

        elif callback_data.action == 'demote':
            user.is_partner = False
            user.source = None

        elif callback_data.action == 'source':
            if callback_data.int_value:
                sources = state_data['sources']
                if not user.is_partner:
                    await bot.send_message(chat_id=user.id, text=f"🔔 <b>{user.full_name}, Ваш статус підвищено до партнера! Перейдіть до функціоналу, натиснувши</b>: /start")

                user.source = callback_data.int_value
                user.source_name = sources[callback_data.int_value]
                user.is_partner = True

        elif callback_data.action == 'is_admin':
            user.is_admin = False if user.is_admin else True

        await repo.session.commit()

        if query.message.chat.id == config.channel.users and callback_data.action == 'source':
            await query.answer(f'{user.full_name} тепер партнер!')
            await query.message.delete()
            return

    await query.message.edit_text(f"👤 <b>{user.full_name}</b>\n"
                                  f"<b>» ID</b>:  {user.id}\n"
                                  f"{f'<b>» Юзернейм</b>:  @{user.username}' if user.username else ''}", reply_markup=kb.user(user))


async def updater(config: Config, session_factory, msg: Message):
    swg_crm = SwaggerCRM(api_key=config.api.swagger_crm)

    async with session_factory() as session:
        repo, page, next_page = Repo(session), 1, True

        await msg.edit_text('↻ <b>Оновлення товарів запущено...</b>')

        while next_page:
            response = await swg_crm.get_request(method='/products', limit='50', page=page)
            for good in response['data']:
                good_db = await repo.get_good(good['sku'])
                if not good_db:
                    await swg_crm.add_good(good, repo)
                else:
                    if good_db.updated_at != good['updated_at']:
                        await repo.delete_good(good['sku'])
                        await swg_crm.add_good(good, repo)
            if response['next_page_url']:
                page += 1
            else:
                next_page = False

        await repo.session.commit()
    await swg_crm.close_session()

    await msg.delete()
    await msg.answer('✔️ <b>Оновлення товарів завершено!</b>', reply_markup=kb.menu())


@router.callback_query(F.data == 'update_goods')
async def update_goods(query: CallbackQuery, config: Config, session_factory):
    msg = await query.message.edit_text('↻ <b>Запускаємо оновлення товарів...</b>')
    await updater(config, session_factory, msg)
