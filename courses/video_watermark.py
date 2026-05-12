from PIL import Image, ImageDraw, ImageFont
import subprocess

def add_watermark_to_video(input_path, output_path, username, email):
    """Add dynamic watermark to video (student name + email)"""
    
    watermark_text = f"© رواق - {username} | {email}"
    
    # Use FFmpeg to draw text watermark
    cmd = [
        'ffmpeg', '-i', input_path,
        '-vf', f"drawtext=text='{watermark_text}':fontcolor=white@0.5:fontsize=24:x=10:y=10",
        '-codec:a', 'copy',
        output_path
    ]
    
    subprocess.run(cmd, check=True)
    return output_path