"""KIS Live UI contracts with injected sessions; no credentials or network."""
from __future__ import annotations

import asyncio
import ast
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from threading import Event

import flet as ft

from data.kis_live import (BookLevel, InstrumentSnapshot, Metrics, OrderBook, SessionSnapshot, Subscription, TradeTick)
from ui.kis_live_page import KISLivePage

NOW = datetime(2030,1,2,1,2,3,tzinfo=timezone.utc)
D = Decimal


def walk(control):
    if not isinstance(control,ft.Control):
        return
    yield control
    for name in ('controls','rows','columns','cells','content','label','title'):
        value=getattr(control,name,None)
        if isinstance(value,ft.Control):
            yield from walk(value)
        elif isinstance(value,(list,tuple)):
            for child in value:
                if isinstance(child,ft.Control):
                    yield from walk(child)


def texts(view):
    return [c.value for c in walk(view) if isinstance(c,ft.Text) and c.value]


class Page:
    def __init__(self):
        self.tasks=[]
        self.updates=0
    def update(self):
        self.updates+=1
    def run_task(self,handler,*args):
        task=asyncio.create_task(handler(*args));self.tasks.append(task);return task
    async def drain(self):
        results=await asyncio.wait_for(asyncio.gather(*tuple(self.tasks),return_exceptions=True),3)
        for result in results:
            if isinstance(result,BaseException) and not isinstance(result,asyncio.CancelledError):
                raise result


async def cleanup(view,page):
    # A failed assertion must release invented stop stalls before loop shutdown.
    if isinstance(view._session,Session):
        view._session.stop_pending=False
    try:
        assert await asyncio.wait_for(view.close_async(),3), 'injected session did not stop'
    finally:
        for task in tuple(page.tasks):
            if not task.done():
                task.cancel()
        await page.drain()


def snapshot(*,status='streaming',reason='',stale=False,indicator=False):
    trade=TradeTick(symbol='005930',market='domestic_equity',tr_id='H0STCNT0',price=D('70200'),
        size=None if indicator else D('3'),cumulative_volume=D('100'),observed_at=NOW,received_at=NOW,
        state='indicator' if indicator else 'trade',delay_seconds=0,time_inferred=True,source_sha256='a'*64)
    book=OrderBook(symbol='005930',market='domestic_equity',tr_id='H0STASP0',
        levels=(BookLevel(bid=D('70100'),bid_size=D('60'),ask=D('70200'),ask_size=D('40')),),
        observed_at=NOW,received_at=NOW,state='regular',delay_seconds=0,time_inferred=True,source_sha256='b'*64)
    values=Metrics(spread=D('100'),imbalance=D('.2'),window_return=D('.01'),
        vwap=None if indicator else D('70150'),sample_count=4,window_seconds=60)
    instrument=InstrumentSnapshot(tr_key='005930',market='domestic_equity',trade=trade,book=book,
        trades=() if indicator else (trade,),metrics=values,trade_stale=stale,book_stale=stale)
    return SessionSnapshot(status=status,reason=reason,connected_at=NOW,last_received_at=NOW,
        subscriptions=(Subscription(tr_id='H0STCNT0',tr_key='005930'),),instruments=(instrument,),reconnect_count=0)


class Session:
    def __init__(self,subscriptions,*,environment):
        self.subscriptions=subscriptions;self.environment=environment
        self.started=0;self.stopped=0;self.status='stopped';self.stop_pending=False
    def start(self):
        self.started+=1;self.status='streaming'
    def stop(self,timeout=3):
        self.stopped+=1;self.status='stopping' if self.stop_pending else 'stopped'
    def snapshot(self):
        return snapshot(status=self.status,reason='STOP_TIMEOUT' if self.status=='stopping' else '',
                        stale=self.status!='streaming')


def select(view):
    view.market.value='domestic_equity';view._refresh_channels()
    view.channel.value='H0STCNT0';view.symbol.value='005930';view._refresh_hint()


def test_build_and_mount_never_construct_or_start_a_session():
    called=[]
    view=KISLivePage(Page(),session_factory=lambda *a,**k:called.append((a,k)))
    view.did_mount()
    assert called==[] and view._session is None
    assert '연결 안 됨' in texts(view)
    assert any('TLS' in value for value in texts(view))
    assert view.received.value.endswith('아직 수신하지 않음')
    assert not view.trades.rows and not view.depth.rows
    assert view.connect_button.on_click is not None
    assert view.stop_button.disabled


def test_connect_companion_subscription_is_explicit_and_stop_cancels_polling():
    async def run():
        page=Page();created=[]
        def factory(*a,**kw):
            result=Session(*a,**kw);created.append(result);return result
        view=KISLivePage(page,session_factory=factory);select(view)
        try:
            await asyncio.wait_for(view.connect_async(),3)
            assert len(created)==1 and created[0].started==1
            assert {s.tr_id for s in created[0].subscriptions}=={'H0STCNT0','H0STASP0'}
            assert all(s.tr_key=='005930' for s in created[0].subscriptions)
            assert view.connect_button.disabled and not view.stop_button.disabled
            view._stop_clicked();await page.drain()
            assert created[0].stopped==1 and view._session is None
            assert view._poll_future is None and view.stop_button.disabled
            assert '연결 안 됨' in texts(view)
        finally:
            await cleanup(view,page)
    asyncio.run(run())


def test_single_channel_choice_does_not_subscribe_a_companion():
    async def run():
        page=Page();view=KISLivePage(page,session_factory=Session);select(view);view.companion.value=False
        try:
            await asyncio.wait_for(view.connect_async(),3)
            assert len(view._session.subscriptions)==1
            assert await asyncio.wait_for(view.close_async(),3)
            await page.drain()
        finally:
            await cleanup(view,page)
    asyncio.run(run())


def test_stop_timeout_retains_session_and_prevents_duplicate_connection():
    async def run():
        page=Page();created=[]
        def factory(*a,**kw):
            result=Session(*a,**kw);created.append(result);return result
        view=KISLivePage(page,session_factory=factory);select(view)
        try:
            await asyncio.wait_for(view.connect_async(),3)
            first=created[0];first.stop_pending=True
            view._stop_clicked();await page.drain()
            assert view._session is first and view.connect_button.disabled and not view.stop_button.disabled
            await asyncio.wait_for(view.connect_async(),3)
            assert len(created)==1 and view._session is first
            assert not await asyncio.wait_for(view.close_async(),3)
            first.stop_pending=False
            assert await asyncio.wait_for(view.close_async(),3)
            assert view._session is None
        finally:
            await cleanup(view,page)
    asyncio.run(run())


def test_unmount_during_start_cannot_restore_or_leak_a_session():
    async def run():
        started=Event();release=Event();page=Page();created=[]
        class SlowSession(Session):
            def start(self):
                started.set();release.wait(2);super().start()
        def factory(*a,**kw):
            item=SlowSession(*a,**kw);created.append(item);return item
        view=KISLivePage(page,session_factory=factory);select(view)
        connecting=asyncio.create_task(view.connect_async())
        try:
            for _ in range(100):
                if started.is_set():break
                await asyncio.sleep(.001)
            assert started.is_set()
            view.will_unmount();release.set()
            await asyncio.wait_for(connecting,3);await page.drain()
            assert created[0].stopped>=1 and view._session is None and view._poll_future is None
        finally:
            release.set()
            try:
                await asyncio.wait_for(connecting,3)
            finally:
                await cleanup(view,page)
    asyncio.run(run())


def test_fresh_snapshot_renders_actual_depth_trades_and_sample_metrics():
    view=KISLivePage(Page(),session_factory=Session)
    view.render_snapshot(snapshot())
    values=texts(view)
    assert '수신 중' in values and '70,200' in values and '+20.00%' in values and '+1.00%' in values
    assert len(view.trades.rows)==1 and len(view.depth.rows)==1
    assert view.depth_balance.visible and abs(view.depth_balance.value-.6)<1e-9
    assert '2030' in view.received.value
    assert '날짜는 수신일 기준으로 추정' in view.detail.value


def test_stale_or_disconnected_values_remain_labelled_and_metrics_are_blank():
    view=KISLivePage(Page(),session_factory=Session)
    for value in (snapshot(stale=True),snapshot(status='reconnecting',reason='DISCONNECTED')):
        view.render_snapshot(value)
        assert '오래된 자료' in texts(view)
        assert all(c.value=='—' for c in walk(view.metrics) if getattr(c,'data',None)=='kis-value')
        assert view.trades.rows and view.depth.rows and not view.depth_balance.visible
        assert '현재 가격으로 사용하지 마세요' in view.trade_note.value


def test_indicator_ticks_are_not_presented_as_completed_trades():
    view=KISLivePage(Page(),session_factory=Session)
    view.render_snapshot(snapshot(indicator=True))
    assert '현재 지표' in texts(view)
    assert not view.trades.rows
    assert '개별 체결 내역을 제공하지 않습니다' in view.trade_note.value
    assert '현재 연결의 수신 표본' in texts(view)


def test_invalid_input_and_backend_error_do_not_expose_external_error_text():
    async def run():
        page=Page();calls=[]
        def bad(*a,**kw):
            calls.append(1);raise RuntimeError('invented-private-text-must-not-appear')
        view=KISLivePage(page,session_factory=bad);select(view);view.symbol.value='invalid/key'
        try:
            await asyncio.wait_for(view.connect_async(),3)
            assert not calls
            view.symbol.value='005930';await asyncio.wait_for(view.connect_async(),3)
            assert calls==[1] and 'invented-private-text-must-not-appear' not in '\n'.join(texts(view))
            view.render_snapshot(snapshot(reason='invented-private-text-must-not-appear'))
            assert 'invented-private-text-must-not-appear' not in '\n'.join(texts(view))
            assert await asyncio.wait_for(view.close_async(),3)
            await page.drain()
        finally:
            await cleanup(view,page)
    asyncio.run(run())


def test_delayed_and_partial_market_coverage_are_visible_before_connect():
    view=KISLivePage(Page(),session_factory=Session)
    view.market.value='overseas_equity';view._refresh_channels();view.channel.value='HDFSCNT0'
    view.symbol.value='DNASAAPL';view._refresh_hint()
    assert 'Nasdaq' in view.latency.value
    view.symbol.value='DHKS00003';view._refresh_hint()
    assert '15분' in view.latency.value
    assert view.companion.disabled


def test_main_wires_navigation_disconnect_and_native_close_without_starting_streams():
    source=(Path(__file__).resolve().parents[1]/'main.py').read_bytes()
    assert b'\r\n' in source and b'\n' not in source.replace(b'\r\n',b'')
    tree=ast.parse(source)
    assert any(isinstance(n,ast.Attribute) and n.attr=='deactivate' for n in ast.walk(tree))
    handlers={n.targets[0].attr for n in ast.walk(tree) if isinstance(n,ast.Assign)
        and len(n.targets)==1 and isinstance(n.targets[0],ast.Attribute)}
    assert {'on_disconnect','on_close','on_event','prevent_close'}<=handlers
    closure=next(n for n in ast.walk(tree) if isinstance(n,ast.AsyncFunctionDef) and n.name=='close_market_streams')
    assert any(isinstance(n,ast.Await) for n in ast.walk(closure))


def test_cached_view_remount_never_labels_disconnected_cached_values_as_live():
    async def run():
        page=Page();view=KISLivePage(page,session_factory=Session);select(view)
        try:
            await asyncio.wait_for(view.connect_async(),3)
            assert '수신 중' in texts(view)
            view.will_unmount();await page.drain()
            assert view._session is None
            view.did_mount()
            assert '연결 안 됨' in texts(view) and '수신 중' not in texts(view)
            assert all(c.value=='—' for c in walk(view.metrics) if getattr(c,'data',None)=='kis-value')
            assert '현재 가격으로 사용하지 마세요' in view.trade_note.value
            assert view._session is None and view._poll_future is None
        finally:
            await cleanup(view,page)
    asyncio.run(run())


def test_wrapped_rows_never_emit_expanded_children_without_a_flex_parent():
    view=KISLivePage(Page(),session_factory=Session)
    rows=[control for control in walk(view) if isinstance(control,ft.Row) and control.wrap]
    assert rows
    for row in rows:
        assert all(not child.expand for child in row.controls), 'Flutter Wrap cannot host Expanded children'
