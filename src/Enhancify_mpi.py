import sys, glob, os, time
import numpy as np

from mpi4py import MPI
from Enhancify_sequential import Enhancify

WORKTAG = 0
DIETAG = 1

# Master process. It distributes the images among the slaves and collects the elapsed times
def master(toProcess, pathsOutput, population, generations, selection, cross_rate, mut_rate, elitism, pressure, verbose):

	n = len(toProcess)
	status = MPI.Status()

	times = np.zeros(len(toProcess))
	idx = 0

	if len(toProcess) == 0:
		# The Master sends the DIETAG to the Slaves
		for i in range(1, size):
			comm.send(obj=None, dest=i, tag=DIETAG)
		return times


	# If the number of the images (n) is higher than the available Slaves (size-1),
	# (size-1) images are run in parallel
	if n > (size-1):
		for i in range(1, size):
			inp = [toProcess[i-1], pathsOutput[i-1], population, generations, selection, cross_rate, mut_rate, elitism, pressure, verbose]
			comm.send(inp, dest=i, tag=WORKTAG)

		# As soon as a Slave is available, the Master assigns it a new image to process
		for i in range(size, n+1):
			im_free, elapsed = comm.recv(source=MPI.ANY_SOURCE, tag=10, status=status)
			times[idx] = elapsed
			idx += 1

			inp = [toProcess[i-1], pathsOutput[i-1], population, generations, selection, cross_rate, mut_rate, elitism, pressure, verbose]
			comm.send(inp, dest=im_free, tag=WORKTAG)

		for i in range(size, n+1):
			im_free, elapsed = comm.recv(source=MPI.ANY_SOURCE, tag=10, status=status)
			times[idx] = elapsed
			idx += 1
	
	# If the number of images (n) is lower than the available cores (size-1),
	# only n Slaves are used
	else:
		for i in range(0, n):
			inp = [toProcess[i], pathsOutput[i], population, generations, selection, cross_rate, mut_rate, elitism, pressure, verbose]
			comm.send(inp, dest=i+1, tag=WORKTAG)

		for i in range(0, n):
			im_free, elapsed = comm.recv(source=MPI.ANY_SOURCE, tag=10, status=status)
			times[idx] = elapsed
			idx += 1

	# The Master sends the DIETAG to the Slaves
	for i in range(1, size):
		comm.send(obj=None, dest=i, tag=DIETAG)

	return times

def slave():

	while True:
		status = MPI.Status()

		# The Slave waits for an image to process
		inp = comm.recv(source=0, tag=MPI.ANY_TAG, status=status)
		elapsed = 0
		
		if inp != None:

			start = time.time()

			# Enhancify execution on the input image by using the provided GA settings
			enhancify = Enhancify(inp[0], inp[1])
			enhancify.startGA(inp[2], inp[3], inp[4], inp[5], inp[6], inp[7], inp[8])

			end = time.time()
			elapsed = end-start

			if inp[9]:
				sys.stdout.write(" * Analyzed image %s"%inp[0])
				sys.stdout.write(" -> Elapsed time %5.2fs on rank %d\n\n" % (elapsed, rank))

		if status.Get_tag():
			break
		
		# The Slave is free to process a new image
		comm.send([rank,elapsed], dest=0, tag=10)

if __name__ == '__main__':

	folderIn   = sys.argv[1]
	folderOut  = sys.argv[2]

	population  = int(sys.argv[3])
	generations = int(sys.argv[4])
	selection   = sys.argv[5]
	cross_rate  = float(sys.argv[6])
	mut_rate    = float(sys.argv[7])
	elitism     = int(sys.argv[8])
	pressure    = int(sys.argv[9])
	verbose     = bool(sys.argv[10])

	comm = MPI.COMM_WORLD
	rank = comm.Get_rank()
	size = comm.Get_size()
	comm.Barrier()

	# Master process
	if rank == 0:
		toProcess   = []
		pathsOutput = []

		alreadyPrint = False
		# Looking for the images in the provided input folder
		listImages = glob.glob(folderIn+os.sep+"*")
		for imagePath in listImages:
			ext = imagePath.split(".")[-1].lower()
			listExts = ["tiff", "tif", "png", "png", "jpeg", "jpg"]

			# Only tiff, png and jpg images can be analyzed
			if ext not in listExts:
				if not alreadyPrint:
					sys.stdout.write("******************************************************************************************\n")
				sys.stdout.write( "Unsupported format. Please provide [")
				for idx,ex in enumerate(listExts):
					if idx == 0:
						sys.stdout.write("'%s', "%ex)
					elif idx == len(listExts)-1:
						sys.stdout.write("'%s'"%ex)
					else:
						sys.stdout.write("'%s', "%ex)

				sys.stdout.write("] images\n")
				
				sys.stdout.write( "Warning %s will be not processed\n\n"%imagePath)
				alreadyPrint = True
				pass

			elif not os.path.exists(imagePath):
				if not alreadyPrint:
					sys.stdout.write("******************************************************************************************\n")
				sys.stdout.write("%s does not exists\n"%imagePath)
				sys.stdout.write( "Warning %s will be not processed\n\n"%imagePath)
				alreadyPrint = True
				pass
			
			else:

				toProcess.append(imagePath)

		if verbose and len(toProcess) > 0:
			sys.stdout.write("******************************************************************************************\n")
			sys.stdout.write("* Running the MPI version of Enhancify\n\n")

			sys.stdout.write( " * GA settings\n")
			sys.stdout.write( "   -> Number of chromosome: %d\n"%population)
			sys.stdout.write( "   -> Number of elite chromosomes: %d\n"%elitism)
			sys.stdout.write( "   -> Number of generations: %d\n"%generations)
			sys.stdout.write( "   -> Crossover rate: %.2f\n"%cross_rate)
			sys.stdout.write( "   -> Mutation rate:  %.2f\n"%mut_rate)

			if selection == 'wheel':
				sys.stdout.write( "   -> Selection: wheel roulette\n\n\n")
			elif selection == 'ranking':
				sys.stdout.write( "   -> Selection: ranking \n\n\n")
			else:
				sys.stdout.write( "   -> Selection: tournament with %d individuals\n\n\n"%pressure)

		if len(toProcess) > 0:

			if not os.path.exists(folderOut):
				os.makedirs(folderOut)

			for i in xrange(len(toProcess)):

				# Output folders
				string    = toProcess[i].split("/")[1:]

				subfolder = string[-1].split(".")[:-1]

				pathOutput = folderOut+os.sep+subfolder[0]

				if not os.path.exists(pathOutput):
					os.makedirs(pathOutput)

				pathsOutput.append(pathOutput)

			sys.stdout.write(" * Enhancify is using %d cores\n\n\n" % (size))

		startAll = time.time()
		times = master(toProcess, pathsOutput, population, generations, selection, cross_rate, mut_rate, elitism, pressure, verbose)

	# Slave process
	else:
		slave()

	comm.Barrier()
	if rank == 0:
		endAll     = time.time()
		elapsedAll = endAll-startAll

		if len(toProcess) == 0:
			sys.stdout.write("******************************************************************************************\n")

		if verbose and len(toProcess) > 0:
			if len(toProcess) > 1:
				sys.stdout.write("\n * Total elapsed time %5.2fs for computing %d images\n" % (elapsedAll, len(toProcess)))
				sys.stdout.write(" * Mean elapsed time  %5.2fs per image\n" % (np.mean(times)))
				sys.stdout.write("******************************************************************************************\n")