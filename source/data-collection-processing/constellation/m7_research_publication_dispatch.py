"""Dispatch research publication through the shared m7 lifecycle lock."""
import fcntl
from constellation.m7_lifecycle import STATE,dispatch

def main():
    with (STATE.parent/'m7-lifecycle.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        dispatch('optima-m7-research-publication.service')

if __name__=='__main__':main()
