"""Explicitly connected KIS market-data view; construction never starts a feed."""
from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Callable

import flet as ft

from core.theme import active
from data.kis_live import LiveSession, Subscription, supported_channels
from data.kis_live_catalog import companion_channel, subscription_delay_seconds, validate_subscription
from ui.components import card, chip, notice, section

MARKETS = (
    ('domestic_equity', '국내 주식'), ('overseas_equity', '해외 주식'),
    ('domestic_derivative', '국내 선물·옵션'), ('overseas_derivative', '해외 선물·옵션'),
    ('bond', '장내 채권'), ('domestic_index', '국내 지수'),
    ('etf_indicator', 'ETF 지표'), ('elw', 'ELW'),
)
_STATUS = {'stopped': ('연결 안 됨', 'muted'), 'connecting': ('연결 중', 'accent'),
    'streaming': ('수신 중', 'success'), 'stopping': ('종료 중', 'warning'), 'reconnecting': ('재연결 중', 'warning'), 'error': ('연결 오류', 'error')}
_REASONS = {
    'NO_CREDENTIALS': 'KIS 연결 정보가 없습니다. Settings에서 설정 안내를 확인하세요.',
    'INVALID_SUBSCRIPTION': '선택한 시장·채널의 종목 코드 형식을 확인하세요.',
    'APPROVAL_FAILED': 'KIS 접속 승인을 받지 못했습니다. 설정과 이용 권한을 확인하세요.',
    'CONNECTION_FAILED': '시세 서버에 연결하지 못했습니다. 네트워크와 이용 시간을 확인하세요.',
    'SUBSCRIPTION_REJECTED': 'KIS가 이 채널 구독을 승인하지 않았습니다. 종목과 이용 권한을 확인하세요.',
    'INVALID_FRAME': '해석할 수 없는 시세를 제외했습니다. 연결 상태를 확인하세요.',
    'DISCONNECTED': '연결이 끊겼습니다. 남아 있는 값은 마지막 수신 자료입니다.',
    'IDLE_TIMEOUT': '수신이 지연되고 있습니다. 휴장·거래 중단·연결 상태를 확인하세요.',
    'RECONNECT_LIMIT': '재연결 횟수를 초과했습니다. 상태를 확인한 뒤 다시 연결하세요.',
    'STOP_TIMEOUT': '연결 정리를 기다리고 있습니다. 즉시 재연결하지 마세요.',
    'CLOCK_INVALID': '시각을 확인할 수 없습니다. PC 시간을 확인하세요.',
    'UNSUPPORTED_NORMALIZATION': '이 채널의 가격·시각 형식은 아직 확인이 필요합니다.',
    'UNSUBSCRIBED_FRAME': '선택하지 않은 채널의 자료를 제외했습니다.',
    'OUT_OF_ORDER_FRAME': '시각 순서가 맞지 않는 자료를 제외했습니다.',
    'ALREADY_RUNNING': '기존 연결이 종료된 뒤 다시 연결할 수 있습니다.',
}
_GENERIC_ERROR = '시세 연결을 처리하지 못했습니다. 설정과 연결 상태를 확인하세요.'
_STALE = '오래된 자료 · 현재 가격으로 사용하지 마세요'
_KIND = {'trade': '체결', 'book': '호가', 'indicator': '지표'}


def _number(value, *, percent=False):
    if type(value) is not Decimal or not value.is_finite():
        return '—'
    if percent:
        return f'{value * 100:+,.2f}%'
    return f'{value:,.8f}'.rstrip('0').rstrip('.') if value != value.to_integral_value() else f'{value:,.0f}'


def _time(value):
    if type(value) is not datetime or value.utcoffset() is None:
        return '아직 수신하지 않음'
    return value.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')


def _safe_reason(reason):
    return _REASONS.get(reason, _GENERIC_ERROR) if reason else ''


class KISLivePage(ft.Container):
    """One read-only session, stopped on navigation, unmount or application close.

    All feed ownership changes run on the page loop under a single async lock.
    Generation checks prevent an old start/poll from restoring a stopped view.
    Session factories are injectable solely for keyless UI tests.
    """
    def __init__(self, page, *, on_open_settings: Callable | None = None,
                 session_factory=LiveSession, poll_seconds=0.5):
        self._host = page
        self._factory = session_factory
        self._poll_seconds = poll_seconds
        self._session = None
        self._poll_future = None
        self._cleanup_future = None
        self._generation = 0
        self._active = True
        self._busy = False
        self._lock = asyncio.Lock()
        self._channels = {}
        self._all_channels = {}
        self._last_snapshot = None
        pal = active()
        self.market = ft.Dropdown(label='시장', width=205, value='domestic_equity',
            options=[ft.dropdown.Option(key, label) for key, label in MARKETS], on_select=self._selection_changed,
            data='kis-market')
        self.environment = ft.Dropdown(label='접속 환경', width=155, value='production',
            options=[ft.dropdown.Option('production', '실전 시세'), ft.dropdown.Option('paper', '모의 환경')],
            on_select=self._selection_changed, data='kis-environment')
        self.channel = ft.Dropdown(label='시세 채널', width=340, options=[], on_select=self._channel_changed,
            data='kis-channel')
        self.symbol = ft.TextField(label='종목 코드', value='', width=245, max_length=40,
            on_change=self._symbol_changed, on_submit=self._connect_clicked, data='kis-symbol')
        self.companion = ft.Switch(label='체결·호가 함께', value=True, on_change=self._channel_changed,
                                   data='kis-companion')
        self.companion_note = ft.Text('', size=11, color=pal.muted, data='kis-companion-note')
        self.connect_button = ft.Button('연결', icon=ft.Icons.LINK, on_click=self._connect_clicked, data='kis-connect')
        self.stop_button = ft.OutlinedButton('중지', icon=ft.Icons.STOP_CIRCLE_OUTLINED,
            on_click=self._stop_clicked, disabled=True, data='kis-stop')
        self.status = ft.Row([chip('연결 안 됨')], spacing=8, wrap=True, data='kis-status')
        self.received = ft.Text('마지막 수신: 아직 수신하지 않음', size=11, color=pal.muted, data='kis-last-received')
        self.message = ft.Text('시장과 채널을 선택하고 종목 코드를 입력한 뒤 연결하세요.',
            size=12, color=pal.muted, selectable=True, data='kis-message')
        self.key_hint = ft.Text('', size=11, color=pal.muted, selectable=True, data='kis-key-hint')
        self.latency = ft.Text('', size=11, color=pal.warning, data='kis-latency')
        self.detail = ft.Text('연결 전 · 자동 연결 없음', size=11, color=pal.muted, data='kis-detail')
        self.metrics = ft.ResponsiveRow(spacing=12, run_spacing=12, data='kis-metrics')
        self.trade_note = ft.Text('체결 채널을 연결하면 최근 수신 체결이 표시됩니다.', size=11, color=pal.muted,
            data='kis-trade-note')
        self.book_note = ft.Text('호가 채널을 연결하면 가격별 잔량이 표시됩니다.', size=11, color=pal.muted,
            data='kis-book-note')
        self.trades = ft.DataTable(columns=[ft.DataColumn(ft.Text(v, size=11)) for v in ('시세 시각', '가격', '수량')],
            rows=[], column_spacing=22, horizontal_margin=0, data_row_min_height=32, data_row_max_height=36,
            heading_row_height=32, data='kis-trades')
        self.depth = ft.DataTable(columns=[ft.DataColumn(ft.Text(v, size=11)) for v in
            ('매수 잔량', '매수 가격', '매도 가격', '매도 잔량')], rows=[], column_spacing=18,
            horizontal_margin=0, data_row_min_height=32, data_row_max_height=36, heading_row_height=32,
            data='kis-depth')
        self.depth_balance = ft.ProgressBar(value=None, visible=False, color=pal.success, bgcolor=pal.error,
            height=5, border_radius=3, data='kis-depth-balance')
        heading = ft.Row([section('KIS Live', subtitle='체결 · 호가 · 수신 구간 지표'),
            ft.OutlinedButton('Settings', icon=ft.Icons.SETTINGS_OUTLINED,
                on_click=lambda _:on_open_settings() if on_open_settings else None,
                disabled=on_open_settings is None)], wrap=True, spacing=12,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        controls = [heading, card(ft.Column([
            ft.Row([self.market, self.environment, self.channel], wrap=True, spacing=12),
            ft.Row([self.symbol, self.connect_button, self.stop_button], wrap=True, spacing=12),
            self.key_hint, ft.Row([self.companion, self.companion_note], wrap=True, spacing=12), self.latency,
            ft.Text('KIS 공식 시세 소켓은 TLS로 암호화되지 않습니다. 신뢰할 수 있는 네트워크에서 연결하세요. '
                    '소켓에는 임시 접속 승인값만 전달하며 앱 비밀값은 보내지 않습니다.',
                    size=11, color=pal.warning, data='kis-transport-note'),
            ft.Divider(color=pal.border),
            ft.Row([self.status, self.received], wrap=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.message, self.detail,
        ], spacing=10)), self.metrics,
        ft.ResponsiveRow([
            card(ft.Column([ft.Text('호가 잔량', size=17, weight=ft.FontWeight.W_600, color=pal.text),
                self.book_note, self.depth_balance, ft.Row([self.depth], scroll=ft.ScrollMode.AUTO)], spacing=10),
                col={'xs':12, 'lg':7}),
            card(ft.Column([ft.Text('최근 체결', size=17, weight=ft.FontWeight.W_600, color=pal.text),
                self.trade_note, ft.Row([self.trades], scroll=ft.ScrollMode.AUTO)], spacing=10),
                col={'xs':12, 'lg':5}),
        ], spacing=12, run_spacing=12),
        notice('조회 전용입니다. 파생상품·채권 정보가 표시되어도 주문 가능 여부를 뜻하지 않습니다. '
               '시장 이용 권한과 지연 시세 여부는 별도로 적용됩니다.', 'muted'),
        ft.Text('지표는 현재 연결에서 받은 표본만 사용합니다. 수익 예측이나 투자 조언이 아니며, '
                '누락·지연된 자료는 보완되지 않습니다.', size=11, color=pal.muted)]
        super().__init__(content=ft.Column(controls, spacing=16, scroll=ft.ScrollMode.AUTO), expand=True,
                         data='kis-live-page')
        self._refresh_channels()
        self._empty_metrics()

    def did_mount(self):
        self._active = True
        if self._session is None and not self._busy:
            self.status.controls = [chip('연결 안 됨')]
            self.connect_button.disabled = not bool(self._channels)
            self.stop_button.disabled = True
            self._empty_metrics()
            if self.trades.rows or self.depth.rows:
                self._stale_tables()
                self.message.value = '연결이 중지되어 있습니다. 남아 있는 값은 마지막 수신 자료입니다.'
        self._update()

    def will_unmount(self):
        self.deactivate()

    def _update(self):
        if self._active:
            try:
                self._host.update()
            except Exception:
                pass  # View may have been removed while a queued update completed.

    def _schedule(self, task, *args):
        try:
            return self._host.run_task(task, *args)
        except Exception:
            return None

    def _invalidate(self):
        self._generation += 1
        if self._poll_future is not None:
            self._poll_future.cancel()
            self._poll_future = None

    def deactivate(self):
        self._active = False
        self._invalidate()
        self._cleanup_future = self._schedule(self._stop_session, False)
        if self._cleanup_future is None and self._session is not None:
            try:
                self._session.stop(timeout=0)
            except Exception:
                pass  # Loop is gone; retain ownership for explicit shutdown retry.
        return self._cleanup_future

    async def close_async(self):
        """Await before native window destruction; idempotent and network-close only."""
        self._active = False
        self._invalidate()
        stopped = await self._stop_session(retain=False)
        if not stopped:
            self._active = True
            self.status.controls = [chip('종료 확인 필요', 'warning')]
            self.message.value = _REASONS['STOP_TIMEOUT']
            self.connect_button.disabled = True
            self.stop_button.disabled = False
            self._update()
        return stopped

    def _refresh_channels(self):
        self._all_channels = {c.tr_id:c for c in supported_channels(self.environment.value)}
        available = tuple(c for c in self._all_channels.values() if c.market == self.market.value)
        self._channels = {c.tr_id:c for c in available}
        previous = self.channel.value
        self.channel.options = [ft.dropdown.Option(c.tr_id, f'{_KIND.get(c.kind, "시세")} · {c.label}')
                                for c in available]
        self.channel.value = previous if previous in self._channels else (available[0].tr_id if available else None)
        self.channel.disabled = not bool(available)
        self.connect_button.disabled = not bool(available) or self._busy
        if not available:
            self.message.value = '이 시장·환경에서 검증된 실시간 채널이 아직 없습니다. 다른 시장이나 환경을 선택하세요.'
        self._refresh_hint()

    def _companion_channel(self):
        try:
            other = companion_channel(self.channel.value, (self.symbol.value or '').strip(),
                                      paper=self.environment.value == 'paper')
            return other if other is not None and other.tr_id in self._all_channels else None
        except (ValueError, TypeError):
            return None

    def _refresh_hint(self):
        item = self._channels.get(self.channel.value)
        self.key_hint.value = item.key_hint if item else '문서 확인 또는 시각·수신 형식 검증이 필요한 채널은 연결할 수 없습니다.'
        self.latency.value = ''
        if item:
            try:
                delay = subscription_delay_seconds(item.tr_id, self.symbol.value or '')
            except (ValueError, TypeError):
                delay = item.delay_seconds
            if delay:
                self.latency.value = f'지연 시세 · 최소 {delay // 60}분 지연. 실시간 신호로 사용하지 마세요.'
            if item.market == 'overseas_equity' and (self.symbol.value or '').startswith(('DNAS','DNYS','DAMS')):
                self.latency.value += ' 미국 무료 시세는 Nasdaq 계열 체결·호가만 포함하며 전체 시장과 다를 수 있습니다.'
        other = self._companion_channel()
        self.companion.disabled = other is None
        self.companion_note.value = (f'같은 시장의 {other.label}도 함께 수신합니다.' if other is not None
            and self.companion.value else '선택한 채널만 수신합니다.' if other is not None else
            '호환되는 종목 코드를 입력하면 같은 시장의 체결·호가를 함께 연결할 수 있습니다.')
        self.symbol.hint_text = '채널 안내에 맞는 종목 코드'

    def _selection_changed(self, _=None):
        self._invalidate()
        self._schedule(self._stop_session, False)
        self._refresh_channels()
        self._clear_data()
        self._update()

    def _channel_changed(self, _=None):
        self._invalidate()
        self._schedule(self._stop_session, False)
        self._refresh_hint()
        self._clear_data()
        self._update()

    def _symbol_changed(self, _=None):
        if self._session is not None or self._busy:
            self._invalidate()
            self._schedule(self._stop_session, False)
        self._clear_data()
        self._refresh_hint()
        self._update()

    def _connect_clicked(self, _=None):
        self._schedule(self.connect_async)

    def _stop_clicked(self, _=None):
        self._invalidate()
        self._schedule(self._stop_session, True)

    async def connect_async(self):
        async with self._lock:
            if self._busy or not self._active:
                return
            self._busy = True
            self._invalidate()
            generation = self._generation
            old = self._session
            if old is not None and not await self._shutdown(old):
                self._busy = False
                self.message.value = _REASONS['STOP_TIMEOUT']
                self.connect_button.disabled = True
                self.stop_button.disabled = False
                self._update()
                return
            self._session = None
            self._clear_data()
            self.connect_button.disabled = True
            self.stop_button.disabled = False
            self.message.value = '선택한 채널에 연결하고 있습니다.'
            self.status.controls = [chip('연결 중', 'accent')]
            self._update()
            session = None
            try:
                tr_id, tr_key = self.channel.value, (self.symbol.value or '').strip()
                if tr_id not in self._channels:
                    raise ValueError('unsupported channel')
                validate_subscription(tr_id, tr_key, paper=self.environment.value == 'paper')
                subscriptions = [Subscription(tr_id=tr_id, tr_key=tr_key)]
                other = self._companion_channel() if self.companion.value else None
                if other is not None:
                    subscriptions.append(Subscription(tr_id=other.tr_id, tr_key=tr_key))
                session = self._factory(tuple(subscriptions), environment=self.environment.value)
                self._session = session
                await asyncio.to_thread(session.start)
                if generation != self._generation or not self._active:
                    stopped = await self._shutdown(session)
                    if stopped and self._session is session:
                        self._session = None
                    return
                self.render_snapshot(session.snapshot())
                self._poll_future = self._schedule(self._poll, generation, session)
                if self._poll_future is None:
                    if await self._shutdown(session):
                        self._session = None
                    self.message.value = _GENERIC_ERROR
            except asyncio.CancelledError:
                stopped = session is None or await self._shutdown(session)
                if stopped and self._session is session:
                    self._session = None
                raise
            except Exception:
                stopped = session is None or await self._shutdown(session)
                if stopped:
                    self._session = None
                if generation == self._generation and self._active:
                    self.status.controls = [chip('연결 오류', 'error')]
                    self.message.value = _REASONS['INVALID_SUBSCRIPTION'] if session is None else _GENERIC_ERROR
                    self._empty_metrics()
            finally:
                self._busy = False
                self.connect_button.disabled = not bool(self._channels) or self._session is not None
                self.stop_button.disabled = self._session is None
                self._update()

    async def _shutdown(self, session):
        try:
            await asyncio.to_thread(session.stop)
            return session.snapshot().status == 'stopped'
        except Exception:
            return False

    async def _stop_session(self, retain=False):
        async with self._lock:
            session = self._session
            stopped = session is None or await self._shutdown(session)
            if stopped:
                self._session = None
            if self._active:
                if retain and session is not None:
                    try:
                        self.render_snapshot(session.snapshot())
                    except Exception:
                        self.message.value = _GENERIC_ERROR
                self.status.controls = [chip('연결 안 됨' if stopped else '종료 확인 필요',
                                             'muted' if stopped else 'warning')]
                self.connect_button.disabled = not bool(self._channels) or not stopped
                self.stop_button.disabled = stopped
                self._empty_metrics()
                if not stopped:
                    self.message.value = _REASONS['STOP_TIMEOUT']
                elif retain or self.trades.rows or self.depth.rows:
                    self.message.value = '연결을 중지했습니다. 남아 있는 값은 마지막 수신 자료입니다.'
                    self._stale_tables()
                self._update()
            return stopped

    async def _poll(self, generation, session):
        try:
            while self._active and generation == self._generation and self._session is session:
                self.render_snapshot(session.snapshot())
                await asyncio.sleep(self._poll_seconds)
        except asyncio.CancelledError:
            return
        except Exception:
            if generation == self._generation:
                self._generation += 1
                self._poll_future = None
                self.message.value = _GENERIC_ERROR
                await self._stop_session(retain=True)

    def _stale_tables(self):
        self.trade_note.value = self.book_note.value = _STALE
        for table in (self.trades, self.depth):
            for row in table.rows:
                for cell in row.cells:
                    cell.content.color = active().muted

    def _metric(self, label, value, detail=''):
        pal = active()
        return card(ft.Column([ft.Text(label, size=11, color=pal.muted),
            ft.Text(value, size=22, weight=ft.FontWeight.W_600, color=pal.text, data='kis-value'),
            ft.Text(detail, size=10, color=pal.muted)], spacing=4), col={'xs':6,'md':4,'xl':2})

    def _empty_metrics(self):
        self.metrics.controls = [self._metric(label, '—', detail) for label, detail in (
            ('최근 가격','체결 채널'),('스프레드','최우선 매도 − 매수'),('호가 불균형','(매수 − 매도 잔량) / 전체'),
            ('표본 구간 수익률','연결 후 수신 표본'),('표본 VWAP','가격 × 수량 / 수량'),('표본 수','유효한 수신 체결'))]
        self.depth_balance.visible = False

    def _clear_data(self):
        self.trades.rows = []
        self.depth.rows = []
        self.received.value = '마지막 수신: 아직 수신하지 않음'
        self.trade_note.value = '체결 채널을 연결하면 최근 수신 체결이 표시됩니다.'
        self.book_note.value = '호가 채널을 연결하면 가격별 잔량이 표시됩니다.'
        self.status.controls = [chip('연결 안 됨')]
        self.message.value = ('시장과 채널을 선택하고 종목 코드를 입력한 뒤 연결하세요.' if self._channels else
            '이 시장·환경에서 검증된 실시간 채널이 아직 없습니다. 다른 시장이나 환경을 선택하세요.')
        self._empty_metrics()

    def render_snapshot(self, snapshot):
        """Render supplied immutable values; never starts, retries or fetches data."""
        self._last_snapshot = snapshot
        pal = active()
        state, token = _STATUS.get(snapshot.status, ('상태 확인 필요', 'warning'))
        self.status.controls = [chip(state, token)]
        self.received.value = '마지막 수신: ' + _time(snapshot.last_received_at)
        self.message.value = _safe_reason(snapshot.reason) or ('선택한 채널의 시세를 수신하고 있습니다.'
            if snapshot.status == 'streaming' else '연결 상태를 확인하고 있습니다.')
        self.detail.value = f'현재 연결의 표본만 표시 · 재연결 {snapshot.reconnect_count}회 · 시각은 PC 시간대'

        if not snapshot.instruments:
            self.trades.rows = []
            self.depth.rows = []
            self._empty_metrics()
            self._update()
            return
        instrument = snapshot.instruments[0]
        trade, book, metrics = instrument.trade, instrument.book, instrument.metrics
        self.detail.value += f' · 표본 연속성 끊김 {instrument.continuity_breaks}회'
        is_indicator = trade is not None and trade.state == 'indicator'
        if any(value is not None and value.time_inferred for value in (trade, book)):
            self.detail.value += ' · 원문에 날짜가 없어 시세 날짜는 수신일 기준으로 추정'
        if any(value is not None and value.delay_seconds > 0 for value in (trade, book)):
            self.status.controls.append(chip('지연 시세', 'warning'))
        live = snapshot.status == 'streaming'
        trade_fresh = live and not instrument.trade_stale
        book_fresh = live and not instrument.book_stale
        self.trade_note.value = (_STALE if trade is not None and not trade_fresh else
            '최근 수신 체결 · 최대 20건 · 최신순' if trade is not None else '이 채널에서는 체결 자료가 아직 없습니다.')
        if is_indicator:
            self.trade_note.value = '지표 채널은 개별 체결 내역을 제공하지 않습니다.'
        self.book_note.value = (_STALE if book is not None and not book_fresh else
            '최우선 호가부터 최대 10단계 · 잔량 기준' if book is not None else '이 채널에서는 호가 자료가 아직 없습니다.')
        if (trade is not None and not trade_fresh) or (book is not None and not book_fresh):
            self.status.controls.append(chip('오래된 자료', 'warning'))
        self.metrics.controls = [
            self._metric('현재 지표' if is_indicator else '최근 가격', _number(trade.price) if trade is not None and trade_fresh else '—', '수신 지표' if is_indicator else '체결 채널'),
            self._metric('스프레드', _number(metrics.spread) if book_fresh else '—', '최우선 매도 − 매수'),
            self._metric('호가 불균형', _number(metrics.imbalance, percent=True) if book_fresh else '—', '잔량 기준 · 매수 우세 +'),
            self._metric('표본 구간 수익률', _number(metrics.window_return, percent=True) if trade_fresh else '—',
                         f'최근 {metrics.window_seconds}초 수신 표본'),
            self._metric('표본 VWAP', _number(metrics.vwap) if trade_fresh else '—', '수신 체결의 거래량 가중평균'),
            self._metric('표본 수', str(metrics.sample_count) if trade_fresh else '—',
                         '현재 연결의 수신 표본' if is_indicator else '현재 연결의 유효한 체결'),
        ]
        trades = tuple(instrument.trades)[-20:]
        self.trades.rows = [ft.DataRow(cells=[ft.DataCell(ft.Text(text, size=11, color=pal.text if trade_fresh else pal.muted))
            for text in (_time(t.observed_at), _number(t.price), _number(t.size))]) for t in reversed(trades)]
        self.depth.rows = [ft.DataRow(cells=[ft.DataCell(ft.Text(text, size=12, color=color,
            font_family='Consolas, monospace')) for text, color in (
                (_number(level.bid_size), pal.muted), (_number(level.bid), pal.success if book_fresh else pal.muted),
                (_number(level.ask), pal.error if book_fresh else pal.muted), (_number(level.ask_size), pal.muted))])
            for level in (book.levels[:10] if book is not None else ())]
        imbalance = metrics.imbalance if book_fresh else None
        self.depth_balance.visible = type(imbalance) is Decimal and imbalance.is_finite() and -1 <= imbalance <= 1
        if self.depth_balance.visible:
            self.depth_balance.value = float((imbalance + 1) / 2)
        self._update()


def build_kis_live_page(page, *, on_open_settings=None):
    return KISLivePage(page, on_open_settings=on_open_settings)
