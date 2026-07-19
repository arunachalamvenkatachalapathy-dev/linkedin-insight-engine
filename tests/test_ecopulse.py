import sys
import os

# Ensure the scripts directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from agents.copywriter import sounds_generic, within_length_band

def test_sounds_generic():
    assert sounds_generic("This is a game changer for environmental engineering") == True
    assert sounds_generic("This is a paradigm shift in our thinking") == True
    assert sounds_generic("A solid, factual post about constructed wetlands configuration.") == False

def test_within_length_band():
    band = {"min_words": 10, "max_words": 20}
    
    # 15 words is within range
    assert within_length_band("word " * 15, band) == True
    
    # 5 words is below range (min 10 * 0.85 = 8.5)
    assert within_length_band("word " * 5, band) == False
