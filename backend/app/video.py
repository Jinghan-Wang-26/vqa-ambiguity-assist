"""Video ambiguity module (optional).
Recommended approach:
- accept short mp4 (<= 6-10s)
- extract frames (e.g., every 0.8s, cap at 12 frames) via ffmpeg
- run build_inventory per frame
- align objects across frames
- answer: describe temporal ambiguity (occlusion, moving in/out, etc.)

This is intentionally left as a stub until you decide to enable ffmpeg dependency.
"""
