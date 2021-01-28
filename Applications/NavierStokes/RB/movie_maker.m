writerObj = VideoWriter('YourAVI.avi');
open(writerObj);
for K = 10 : 99
  filename = sprintf('MOVIE/rbmov.00%2d.png', K);
  thisimage = imread(filename);
  writeVideo(writerObj, thisimage);
end
close(writerObj);