#
# derived from https://github.com/happyhorseskull/you-can-datamosh-on-linux
# MIT License
# Do what you will with this
# 

import sys, os, subprocess, random
from argparse import ArgumentParser, ArgumentTypeError
import tempfile

def bail_on_notfile(path):
  '''Validator for file existence for use in argparsing'''
  if not os.path.isfile(path):
    raise ArgumentTypeError("Couldn't find {} - check path".format(path))
  else:
    return path

def tempFilename(ext):
  return tempfile.mktemp(ext)


def processVidBase(inputVid, outputVid, outputWidth, fps, repeatPFrames):
  print(inputVid, outputVid, outputWidth, fps, repeatPFrames)

  aviFile = tempFilename(".avi")
  print(aviFile)
  # convert original file to avi
  cmd = 'ffmpeg -loglevel error -y -i ' + inputVid + ' ' + ' -crf 0 -pix_fmt yuv420p -r ' + str(fps) + ' ' + aviFile
  subprocess.call(cmd, shell=True)

  outputAvi = tempFilename(".avi")
  # open up the new files so we can read and write bytes to them
  in_file  = open(aviFile,  'rb')
  out_file = open(outputAvi, 'wb')
  
  # because we used 'rb' above when the file is read the output is in byte format instead of Unicode strings
  in_file_bytes = in_file.read()

  # 0x30306463 which is ASCII 00dc signals the end of a frame. '0x' is a common way to say that a number is in hexidecimal format.
  frames = in_file_bytes.split(bytearray.fromhex('30306463'))

  # 0x0001B0 signals the beginning of an i-frame. Additional info: 0x0001B6 signals a p-frame
  iframe = bytearray.fromhex('0001B0')

  # We want at least one i-frame before the glitching starts
  i_frame_yet = False

  frameSet = []

  for index, frame in enumerate(frames):
    frameType = "p"
    if frame[5:8] == iframe:
      frameType = "i"

    if frameSet == []:
      fd = (frameType, [frame])
      frameSet.append(fd)
    else:
      if frameSet[-1][0] == frameType:
        frameSet[-1][1].append(frame)
      else:
        fd = (frameType, [frame])
        frameSet.append(fd)

  for frameTuple in frameSet:
   frames = frameTuple[1]
   random.shuffle(frames)
   for frame in frames:
     out_file.write(frame + bytearray.fromhex('30306463'))

  for index, frame in enumerate(frames):

    #or index < int(start_effect_sec * fps) or index > int(end_effect_sec * fps):
    if  i_frame_yet == False:
      # the split above removed the end of frame signal so we put it back in
      out_file.write(frame + bytearray.fromhex('30306463'))

      # found an i-frame, let the glitching begin
      if frame[5:8] == iframe: i_frame_yet = True

    else:
      # while we're moshing we're repeating p-frames and multiplying i-frames
      if frame[5:8] != iframe:
        # frame = fupframe(frame)
        # this repeats the p-frame x times
        for i in range(repeat_p_frames):
          out_file.write(frame + bytearray.fromhex('30306463'))

  in_file.close()
  out_file.close()
  

  # Convert avi to mp4. If you want a different format try changing the output variable's file extension
  # and commenting out the line that starts with -crf. If that doesn't work you'll be making friends with ffmpeg's many, many options.
  # It's normal for ffmpeg to complain a lot about malformed headers if it processes the end of a datamoshed avi.
  # The -t option specifies the duration of the final video and usually helps avoid the malformed headers at the end.
  tempMp4 = tempFilename(".mp4")
  cmd = 'ffmpeg -loglevel error -y -i ' + outputAvi + ' ' + ' -crf 18 -pix_fmt yuv420p -vcodec libx264 -acodec aac -r ' + str(fps) + ' ' + ' -vf "scale=' + str(outputWidth) + ':-2:flags=lanczos" ' + ' ' + tempMp4
  subprocess.call(cmd, shell=True)

  cmd = 'ffmpeg -y -err_detect ignore_err -i "' + tempMp4 + '" -c:v libx264 -x264opts keyint=48:min-keyint=48:scenecut=-1 -preset medium -crf 22 -c:a copy "'+ outputVid +'"'
  subprocess.call(cmd, shell=True)

def preCompress(inputVideo, nIts):
  tempMp42 = tempFilename(".mp4")
  cmd = 'ffmpeg -i ' + inputVideo + ' -acodec mp2 -c:v libx264 -x264opts keyint=100:min-keyint=100:scenecut=-1 -b:v 200k ' + tempMp42
  subprocess.call(cmd, shell=True)
  tempMp4 = tempMp42

  for i in range(nIts):
    tempMp42 = tempFilename(".mp4")
    cmd = 'ffmpeg -i ' + tempMp4 + ' -acodec mp2 -c:v libx264 -x264opts keyint=100:min-keyint=100:scenecut=-1 -b:v 200k ' + tempMp42
    subprocess.call(cmd, shell=True)
    tempMp4 = tempMp42
    
  return tempMp42
    

def main():
  parser = ArgumentParser()
  parser.add_argument('--input', type = bail_on_notfile, help = 'Input video', required=True)
  parser.add_argument('--output', help = 'Output video', required=True)
  parser.add_argument('--output-width', default = 640, help = 'Width of output video')
  parser.add_argument('--fps', default = 23.976, help = 'FPS of output video')
  parser.add_argument('--repeat_p_frames', default = 2, help = 'Number of p-frames to repeat')
  parser.add_argument('--precompress', default = 0, help = 'Precompression iterations')

  args = parser.parse_args()
  
  if int(args.precompress) == 0:
    processVidBase(args.input, args.output, args.output_width, args.fps, args.repeat_p_frames)
  else:
    precomp = preCompress(args.input, int(args.precompress))
    processVidBase(precomp, args.output, args.output_width, args.fps, args.repeat_p_frames)


if __name__ == "__main__":
  main()
  

#
# # gets rid of the in-between files so they're not crudding up your system
# os.remove(input_avi)
# os.remove(output_avi)
