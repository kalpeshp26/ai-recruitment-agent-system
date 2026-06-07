import traceback
import sys
import os

# Add parent directory to path
sys.path.append(os.getcwd())

from prescreening.answer_evaluator import evaluate_session

try:
    print("Evaluating session 'cfb5da25-c751-46d7-a5de-03a6c9035f8e'...")
    res = evaluate_session('cfb5da25-c751-46d7-a5de-03a6c9035f8e')
    print("Result:", res)
except Exception as e:
    print("Caught Exception:", type(e), e)
    traceback.print_exc()
