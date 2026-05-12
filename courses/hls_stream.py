import subprocess
import os

def generate_hls_stream(input_video, output_dir, student_id):
    """Convert video to HLS format with AES-128 encryption"""
    
    # Generate encryption key
    key_file = os.path.join(output_dir, 'enc.key')
    key_info = os.path.join(output_dir, 'enc.keyinfo')
    
    # Generate random key
    subprocess.run(['openssl', 'rand', '-hex', '16'], stdout=open(key_file, 'w'))
    
    # Create key info file
    with open(key_info, 'w') as f:
        f.write(f"{key_file}\n{key_file}\n{os.path.basename(key_file)}")
    
    # Convert to HLS
    cmd = [
        'ffmpeg', '-i', input_video,
        '-hls_time', '10',
        '-hls_key_info_file', key_info,
        '-hls_playlist_type', 'vod',
        '-hls_segment_filename', f'{output_dir}/segment_%03d.ts',
        f'{output_dir}/index.m3u8'
    ]
    
    subprocess.run(cmd, check=True)
    return f'{output_dir}/index.m3u8'