import time
import pytest

@pytest.mark.parametrize("counter", range(30))
def test_sleep(counter):
    # print(f'Hallo {counter}')
    time.sleep(0.5)
    assert counter != 3
