"""Quick test script to verify agent setup."""

import asyncio
import traceback
from src.agent import LifeAdminAgent


async def main():
    print("🚀 Starting Life Admin Assistant...")
    print("-" * 50)
    
    # Create agent
    agent = LifeAdminAgent()
    print(f"✅ Agent created using model: {agent.chat_client.model_id}")
    print("-" * 50)
    
    # Test life event directly
    print("\n🧪 Testing life event creation directly...")
    try:
        from src.tools.checklists import start_life_event
        result = start_life_event(
            event_type="moving",
            title="Test Move",
            target_date="2026-01-15",
            notes=""
        )
        print(f"Direct call result: {result}")
    except Exception as e:
        print(f"❌ Direct call failed: {e}")
        traceback.print_exc()
    
    print("\n" + "-" * 50)
    
    # Test conversation
    test_messages = [
        "Show my moving checklist",
        "Mark Give notice to landlord as complete",
        "List my life events",
    ]
    
    for message in test_messages:
        print(f"\n👤 You: {message}")
        print("🤖 Assistant: ", end="", flush=True)
        
        try:
            async for chunk in agent.chat_stream(message):
                print(chunk, end="", flush=True)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            traceback.print_exc()
        print("\n")


if __name__ == "__main__":
    asyncio.run(main())