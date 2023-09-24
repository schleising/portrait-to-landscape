from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import shutil
import time

from tkinter import Tk, filedialog

from PIL import Image

from ffmpeg import FFmpeg

def main():
    # Create the Tkinter root
    root = Tk()
    root.withdraw()

    # Ask user for input file
    input_file = filedialog.askopenfilename(title='Select input file', filetypes=(('Video files', '*.mp4'), ('All files', '*.*')))

    # Convert the input_file string to a Path object and check that it exists
    input_file = Path(input_file)
    if not input_file.exists():
        print('Input file does not exist')
        return
    
    # Set the portrait and landscape output folders
    portrait_output_path = input_file.parent / 'Portrait'
    landscape_output_path = input_file.parent / 'Landscape'

    # Create the output folders if they don't exist
    portrait_output_path.mkdir(parents=True, exist_ok=True)
    landscape_output_path.mkdir(parents=True, exist_ok=True)

    # Convert input file to frames in portrait mode
    print('Converting input file to frames in portrait mode')
    ffmpeg = (
        FFmpeg()
        .option('y')
        .input(input_file)
        .output(portrait_output_path / '%04d.png')
    )

    try:
        ffmpeg.execute()
    except :
        print('Error converting input file to frames in portrait mode')
        return


    # Convert input file to frames in landscape mode
    print('Converting input file to frames in landscape mode')
    ffmpeg = (
        FFmpeg()
        .option('y')
        .input(input_file)
        .output(
            landscape_output_path / '%04d.png',
            vf='transpose=2'
        )
    )

    ffmpeg.execute()

    # Ask user which frame number to start in landscape mode
    start_frame = int(input('Enter first landscape frame: '))

    # Create an input folder
    input_path = input_file.parent / 'Input'
    input_path.mkdir(parents=True, exist_ok=True)

    # Copy the portrait frames to the input folder
    print('Copying portrait frames to input folder')
    for f in portrait_output_path.glob('*.png'):
        if int(f.stem) < start_frame:
            f.rename(input_path / f.name)

    # Copy the landscape frames to the input folder
    print('Copying landscape frames to input folder')
    for f in landscape_output_path.glob('*.png'):
        if int(f.stem) >= start_frame:
            f.rename(input_path / f.name)

    # Create an output folder for the resized images
    output_path = input_file.parent / 'Output'
    output_path.mkdir(parents=True, exist_ok=True)

    # Resize the images
    print('Resizing the images')
    file_list = list(input_path.glob('*.png'))

    # Start a timer
    start_time = time.perf_counter()

    # Run the tasks concurrently
    with ThreadPoolExecutor() as pool:
        for file in file_list:
            pool.submit(resize_image, file, output_path)

    # Calculate the elapsed time
    elapsed_time = time.perf_counter() - start_time

    # Print the elapsed time
    print(f'Resizing images took: {elapsed_time:.2f} seconds')

    # Combine the frames into a video
    print('Combining frames into a video')
    ffmpeg = (
        FFmpeg()
        .option('y')
        .option('framerate', '30')
        .input(output_path / '%04d.png')
        .output(
            input_file.parent / 'Output.mp4',
            {
                'c:v': 'libx264',
                'pix_fmt': 'yuv420p',
            }
        )
    )

    ffmpeg.execute()

    # Remux the audio from the input file into the video
    print('Remuxing the audio from the input file into the video')
    ffmpeg = (
        FFmpeg()
        .option('y')
        .input(input_file.parent / 'Output.mp4')
        .input(input_file)
        .output(
            input_file.parent / 'Output2.mp4',
            {
                'c:v': 'copy',
                'c:a': 'copy',
            },
            map=['0:0', '1:1']
        )
    )

    ffmpeg.execute()

    # Delete the temporary files
    print('Deleting temporary files')
    shutil.rmtree(portrait_output_path)
    shutil.rmtree(landscape_output_path)
    shutil.rmtree(input_path)
    shutil.rmtree(output_path)
    (input_file.parent / 'Output.mp4').unlink()

def resize_image(f: Path, output_path: Path) -> None:
    image = Image.open(f)

    # Check if the image in in portrait or landscape mode
    if image.height > image.width:
        # Save the image height and width to full image height and width variables, reversing the height and width
        full_image_height = image.width
        full_image_width = image.height

        # Make the image the same height as the final image
        new_height = image.width
        new_width = int(image.width * (new_height / image.height))

        # Resize the image
        image = image.resize((new_width, new_height))

        # Pad the image to make it the same width as the final image
        left_padding = int((full_image_width - new_width) / 2)
        padded_image = Image.new('RGBA', (full_image_width, full_image_height), (0, 0, 0, 0))
        padded_image.paste(image, (left_padding, 0))

        # Save the image
        padded_image.save(output_path / f.name)
    else:
        # Copy the image to the output folder
        image.save(output_path / f.name)

if __name__ == '__main__':
    main()
