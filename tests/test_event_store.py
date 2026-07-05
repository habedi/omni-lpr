import pytest
from mcp.types import JSONRPCMessage, JSONRPCRequest
from omni_lpr.event_store import InMemoryEventStore


@pytest.mark.asyncio
async def test_in_memory_event_store_store_event():
    store = InMemoryEventStore(max_events_per_stream=3)
    
    # Construct a dummy JSON-RPC message
    message = JSONRPCMessage(
        JSONRPCRequest(jsonrpc="2.0", id=1, method="tools/list")
    )
    
    event_id = await store.store_event(stream_id="stream-1", message=message)
    
    # Verify the event ID is generated (non-empty string)
    assert isinstance(event_id, str)
    assert len(event_id) > 0
    
    # Verify it is indexed
    assert event_id in store.event_index
    entry = store.event_index[event_id]
    assert entry.event_id == event_id
    assert entry.stream_id == "stream-1"
    assert entry.message == message
    
    # Verify it is in the stream deque
    assert len(store.streams["stream-1"]) == 1
    assert store.streams["stream-1"][0] == entry


@pytest.mark.asyncio
async def test_in_memory_event_store_eviction():
    # Eviction logic triggers when stream exceeds max_events_per_stream
    store = InMemoryEventStore(max_events_per_stream=2)
    
    msg1 = JSONRPCMessage(JSONRPCRequest(jsonrpc="2.0", id=1, method="tools/call"))
    msg2 = JSONRPCMessage(JSONRPCRequest(jsonrpc="2.0", id=2, method="tools/call"))
    msg3 = JSONRPCMessage(JSONRPCRequest(jsonrpc="2.0", id=3, method="tools/call"))
    
    id1 = await store.store_event("stream-1", msg1)
    id2 = await store.store_event("stream-1", msg2)
    
    assert len(store.streams["stream-1"]) == 2
    assert id1 in store.event_index
    assert id2 in store.event_index
    
    # Adding a 3rd event should evict the 1st event (id1)
    id3 = await store.store_event("stream-1", msg3)
    
    assert len(store.streams["stream-1"]) == 2
    assert id1 not in store.event_index
    assert id2 in store.event_index
    assert id3 in store.event_index
    
    # Verify the deque contents
    assert store.streams["stream-1"][0].event_id == id2
    assert store.streams["stream-1"][1].event_id == id3


@pytest.mark.asyncio
async def test_in_memory_event_store_replay_events_after():
    store = InMemoryEventStore(max_events_per_stream=5)
    
    msg1 = JSONRPCMessage(JSONRPCRequest(jsonrpc="2.0", id=1, method="test-method"))
    msg2 = JSONRPCMessage(JSONRPCRequest(jsonrpc="2.0", id=2, method="test-method"))
    msg3 = JSONRPCMessage(JSONRPCRequest(jsonrpc="2.0", id=3, method="test-method"))
    
    id1 = await store.store_event("stream-1", msg1)
    id2 = await store.store_event("stream-1", msg2)
    id3 = await store.store_event("stream-1", msg3)
    
    replayed_messages = []
    
    async def send_callback(event_message):
        replayed_messages.append(event_message)
        
    # Replaying after id1 should return stream ID and replay id2 and id3
    stream_id = await store.replay_events_after(id1, send_callback)
    
    assert stream_id == "stream-1"
    assert len(replayed_messages) == 2
    assert replayed_messages[0].event_id == id2
    assert replayed_messages[0].message == msg2
    assert replayed_messages[1].event_id == id3
    assert replayed_messages[1].message == msg3


@pytest.mark.asyncio
async def test_in_memory_event_store_replay_after_missing_event():
    store = InMemoryEventStore()
    
    replayed_messages = []
    
    async def send_callback(event_message):
        replayed_messages.append(event_message)
        
    # Replaying with a missing event ID should return None and not invoke callback
    stream_id = await store.replay_events_after("missing-id", send_callback)
    
    assert stream_id is None
    assert len(replayed_messages) == 0
