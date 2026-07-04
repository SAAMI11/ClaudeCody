"""
videopipe — a free, single-prompt AI video pipeline.

Enter one prompt, get a finished short video. Every stage is a swappable
"provider" so the same pipeline runs fully offline (procedural rendering) in a
locked-down sandbox, or against free web services / local open-source models on
your own PC.

Stages:
    prompt  -> brain      (storyboard: scenes, narration, captions)
            -> images     (one still per scene)
            -> motion     (Ken Burns pan/zoom -> clip frames)
            -> subtitles  (burn captions onto frames)
            -> audio      (music bed + optional TTS voiceover)
            -> assemble   (crossfade transitions + H.264/AAC mux -> MP4)
"""

__version__ = "0.1.0"
