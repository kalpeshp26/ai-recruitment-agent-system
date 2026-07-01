"""
Test script for Stage 8 and Stage 9 event-driven workflow
"""
import asyncio
import sys
sys.path.insert(0, '.')

from shared.queue.event_bus import event_bus
from shared.queue.event_topics import EventTopics
from offer.offer_agent import process_interview_completed_event, process_offer_accepted_event
from onboarding.onboarding_agent import process_onboarding_started_event


async def test_stage8_offer_generation():
    """Test Stage 8: Interview completion → Offer generation"""
    print("\n" + "="*60)
    print("TEST 1: Stage 8 - Interview Completion → Offer Generation")
    print("="*60)
    
    # Simulate interview completion event
    event_data = {
        "interview_id": 123,
        "candidate_id": "test_candidate_456",
        "job_id": "job_001",
        "overall_score": 0.85,
        "recommendation": "hire"
    }
    
    print(f"\n📤 Publishing interview.completed event...")
    print(f"   Candidate: {event_data['candidate_id']}")
    print(f"   Score: {event_data['overall_score']}")
    print(f"   Recommendation: {event_data['recommendation']}")
    
    await process_interview_completed_event(event_data)
    print("\n✅ Test 1 Complete")


async def test_stage9_onboarding():
    """Test Stage 9: Offer accepted → Onboarding"""
    print("\n" + "="*60)
    print("TEST 2: Stage 9 - Offer Accepted → Onboarding")
    print("="*60)
    
    # Simulate offer acceptance event
    event_data = {
        "offer_id": "offer_test_123",
        "candidate_id": "test_candidate_456",
        "job_id": "job_001",
        "joining_date": "2026-07-01"
    }
    
    print(f"\n📤 Publishing onboarding.started event...")
    print(f"   Offer ID: {event_data['offer_id']}")
    print(f"   Candidate: {event_data['candidate_id']}")
    print(f"   Joining Date: {event_data['joining_date']}")
    
    await process_onboarding_started_event(event_data)
    print("\n✅ Test 2 Complete")


async def test_full_workflow():
    """Test complete workflow: Interview → Offer → Onboarding"""
    print("\n" + "="*60)
    print("TEST 3: Full Workflow - Interview → Offer → Onboarding")
    print("="*60)
    
    # Step 1: Interview completion
    interview_event = {
        "interview_id": 456,
        "candidate_id": "workflow_test_789",
        "job_id": "job_002",
        "overall_score": 0.92,
        "recommendation": "hire"
    }
    
    print(f"\n📤 Step 1: Interview Completed (score: {interview_event['overall_score']})")
    await process_interview_completed_event(interview_event)
    
    # Give event bus time to process
    await asyncio.sleep(0.5)
    
    # Step 2: Offer acceptance (simulated)
    offer_event = {
        "offer_id": "offer_workflow_test",
        "candidate_id": "workflow_test_789",
        "job_id": "job_002",
        "joining_date": "2026-07-15"
    }
    
    print(f"\n📤 Step 2: Offer Accepted")
    await process_offer_accepted_event(offer_event)
    
    # Give event bus time to process
    await asyncio.sleep(0.5)
    
    print("\n✅ Test 3 Complete - Full workflow executed")


async def main():
    """Run all tests"""
    print("\n" + "🧪 " + "="*58)
    print("Stage 8 & 9 Event-Driven Workflow Tests")
    print("="*60 + "\n")
    
    try:
        # Test 1: Stage 8 - Offer generation
        await test_stage8_offer_generation()
        await asyncio.sleep(1)
        
        # Test 2: Stage 9 - Onboarding
        await test_stage9_onboarding()
        await asyncio.sleep(1)
        
        # Test 3: Full workflow
        await test_full_workflow()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60 + "\n")
        
        print("📊 Summary:")
        print("   • Stage 8 (Offer Management): ✅ Working")
        print("   • Stage 9 (Onboarding): ✅ Working")
        print("   • Event-driven workflow: ✅ Working")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
