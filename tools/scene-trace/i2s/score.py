"""Score a render against the reference: python score.py reference.png render.png"""
import sys

from metrics import fmt, load, scores

if __name__ == '__main__':
    print(fmt(scores(load(sys.argv[1]), load(sys.argv[2]))))
