# SDM model test simulation
import numpy as np
from operator import itemgetter
import pprint
pp = pprint.PrettyPrinter(indent=4)
import argparse
import shlex
import readline
readline.parse_and_bind('tab: complete')



class Env:
	# stores environment settings and data arrays

	# command line arguments, also used for parsing interactive update of parameters
	parms = [
		{ "name":"word_length", "kw":{"help":"Word length for address and memory", "type":int},
	 	  "flag":"w", "require_initialize":True, "default":256 },
	 	{ "name":"num_rows", "kw":{"help":"Number rows in memory","type":int},
	 	  "flag":"r", "require_initialize":True, "default":512 },
	 	{ "name":"activation_count", "kw":{"help":"Number memory rows to activate for each address","type":int},
	 	  "flag":"a", "require_initialize":True, "default":5},
	 	{ "name":"char_match_fraction", "kw": {"help":"Fraction of word_length to form hamming distance threshold for"
			" matching character to item memory","type":float},"flag":"cmf", "require_initialize":False, "default":0.25},
		{ "name":"string_to_store", "kw":{"help":"String to store","type":str,"nargs":'*'}, "require_initialize":False,
		  "flag":"s", "default":'"happy day" "evans hall" "campanile" "sutardja dai hall" "oppenheimer"'
		  ' "distributed memory" "abcdefghijklmnopqrstuvwxyz"'}]

	def __init__(self):
		self.parse_command_arguments()
		self.initialize()

	def parse_command_arguments(self):
		parser = argparse.ArgumentParser(description='Store sequences using a sparse distributed memory.',
			formatter_class=argparse.ArgumentDefaultsHelpFormatter)
		# also make parser for interactive updating parameters (does not include defaults)
		iparse = argparse.ArgumentParser(description='Update sdm parameters.') # exit_on_error=False)
		for p in self.parms:
			parser.add_argument("-"+p["flag"], "--"+p["name"], **p["kw"], default=p["default"])
			iparse.add_argument("-"+p["flag"], "--"+p["name"], **p["kw"])  # default not used for interactive update
		self.iparse = iparse # save for later parsing interactive input
		args = parser.parse_args()
		self.pvals = {p["name"]: getattr(args, p["name"]) for p in self.parms}
		self.pvals["string_to_store"] = shlex.split(self.pvals["string_to_store"])
		self.display_settings()

	def initialize(self):
		# initialize sdm and char_map
		word_length = self.pvals["word_length"]
		self.cmap = Char_map(self.pvals["string_to_store"], word_length=word_length)
		self.sdm = Sdm(address_length=word_length, word_length=word_length, num_rows=self.pvals["num_rows"])

	def display_settings(self):
		print("Current settings:")
		for p in self.parms:
			print(" %s: %s" % (p["name"], self.pvals[p["name"]]))

	def update_settings(self, line):
		instructions = ("Update settings using 'u' followed by KEY VALUE pair(s), where keys are:\n" +
			'; '.join(["-"+p["flag"] + " --"+p["name"] for p in self.parms]))
		#	" -w --world_length; -r --num_rows; -a --activation_count; -cmf --char_match_fraction; -s --string_to_store"
		if len(line) < 5:
			self.display_settings()
			print(instructions)
			return
		try:
			args = self.iparse.parse_args(shlex.split(line))
		except argparse.ArgumentError:
			print('Invalid entry, try again.')
			return
		updated = []
		self.initialize = False
		for p in self.parms:
			name = p["name"]
			val = getattr(args, name)
			if val is not None:
				if self.pvals[name] == val:
					print("%s unchanged (is already %s)" % (name, val))
				else:
					self.pvals[name] = val
					updated.append("%s=%s" % (name, val))
					if p["require_initialize"]:
						self.initialize = True
		if updated:
			print("Updated: %s" % ", ".join(updated))
			self.display_settings()
			print("initialize=%s" % self.initialize)
		else:
			print("Nothing updated")


def do_interactive_commands(env):
	instructions = ("Enter command, control-d to quit\n"
		" s <string> - store new string(s)\n"
		" r <prefix> - recall starting with prefix\n"
		" r - recall stored strings\n"
		" u - update parameters\n"
		" i - initalize memory")
	print(instructions)
	while True:
		try:
			line=input("> ")
		except EOFError:
			break;
		if len(line) == 0 or line[0] not in "srui":
			print(instructions)
			continue
		cmd = line[0]
		arg = "" if len(line) == 1 else line[1:].strip()
		if cmd == "r" and len(arg) > 0:
			print("recall prefix %s" % arg)
			recall_strings(env, shlex.split(arg))
		elif cmd == "r":
			print("recall stored strings")
			recall_param_strings(env)
		elif cmd == "s":
			print("store new string %s" % arg)
			store_strings(env, strings)
		elif cmd == "u":
			print("update parameter settings %s" % arg)
			env.update_settings(arg)
		elif cmd == "i":
			env.initialize()
			print("initialized memory.")
		else:
			sys.exit("Invalid command: %s" % cmd)
	print("\nDone")


# class Sequences:
# 	# sequences learned
# 	def __init__(self, seq = ["happy_day", "evans_hall", "campanile", "sutardja_dai_hall", "oppenheimer"]):
# 		self.seq = seq


# def random_b(word_length):
# 	# return binary vector with equal number of 1's and 0's
# 	assert word_length % 2 == 0, "word_length must be even"
# 	hw = word_length / 2
# 	arr = np.array([1] * hw + [0] * hw, dtype=np.int8)
# 	np.random.shuffle(arr)
# 	return arr

def find_matches(m, b, nret, index_only = False):
	# m is 2-d array of binary values, first dimension if value index, second is binary number
	# b is binary number to match
	# nret is number of top matches to return
	# returns sorted tuple (i, c) where i is index and c is number of non-matching bits (0 is perfect match)
	# if index_only is True, only return the indices, not the c
	assert len(m.shape) == 2, "array to match must be 2-d"
	assert m.shape[1] == len(b), "array element size does not match size of match binary value"
	matches = []
	for i in range(m.shape[0]):
		ndiff = np.count_nonzero(m[i]!=b)
		matches.append( (i, ndiff) )
	matches.sort(key=itemgetter(1))
	hamming = matches[nret-1][1]
	nh = 1
	while matches[nret-1+nh][1] == hamming:
		nh += 1
	if nh > 1:
		print("Found %s  match last hamming: %s" % (nh, matches[nret-1:nret-1+nh]))
	top_matches = matches[0:nret]
	if index_only:
		top_matches = [x[0] for x in top_matches]
	return top_matches

def initialize_binary_matrix(nrows, ncols):
	# create binary matrix with each row having binary random number
	assert ncols % 2 == 0, "ncols must be even"
	bm = np.random.randint(2, size=(nrows, ncols), dtype=np.int8)
	# hw = ncols / 2
	# bm = np.zeros( (nrows, ncols), dtype=dtype=np.int8) # bm - binary_matrix
	# for i in range(nrows):
	# 	bm[i][0:hw] = 1				# set half of row to 1, then shuffle
	# 	np.random.shuffle(bm[i])
	return bm

def merge(b1, b2):
	# merge binary values b1, b2 by taking every other value of each and concationating
	b3 = np.concatenate((b1[0::2],b2[0::2]))
	return b3

class Char_map:
	# maps each character in a sequence to a random binary word
	# below specifies maximum number of unique characters
	max_unique_chars = 50

	def __init__(self, seq, word_length = 128):
		# seq - a Sequence object
		# word_length - number of bits in random binary word
		assert word_length % 2 == 0, "word_length must be even"
		self.word_length = word_length
		self.chars = ''.join(sorted(list(set(list(''.join(seq))))))  # sorted string of characters appearing in seq
		self.chars += "#"  # stop char - used to indicate end of sequence
		self.check_length()
		self.binary_vals = initialize_binary_matrix(self.max_unique_chars, word_length)
	
	def check_length(self):
		# make sure not too many unique characters 
		if len(self.chars) > self.max_unique_chars:
			sys.exit("Too many unique characters (%s) max is %s.  Increase constant: max_unique_chars" % (
				len(self.chars), self.max_unique_chars))

	def char2bin(self, char):
		# return binary word associated with char
		index = self.chars.find(char)
		if index == -1:
			# this is a new character, add it to chars string
			index = len(self.chars)
			self.chars += char
			check_length()
		return self.binary_vals[index]

	def bin2char(self, b, nret = 3):
		# returns array of top matching characters and the hamming distance (# of bits not matching)
		# b is a binary array, same length as word_length
		# nret is the number of matches to return
		assert self.word_length == len(b)
		top_matches = find_matches(self.binary_vals[0:len(self.chars),:], b, nret)
		top_matches = [ (self.chars[x[0]], x[1]) for x in top_matches ]
		return top_matches


class Sdm:
	# implements a sparse distributed memory
	def __init__(self, address_length=128, word_length=128, num_rows=512, nact=5):
		# nact - number of active addresses used (top matches) for reading or writing
		self.address_length = address_length
		self.word_length = word_length
		self.num_rows = num_rows
		self.nact = nact
		self.data_array = np.zeros((num_rows, word_length), dtype=np.int8)
		self.addresses = initialize_binary_matrix(num_rows, word_length)


	def store(self, address, data):
		# store binary word data at top nact addresses matching address
		top_matches = find_matches(self.addresses, address, self.nact, index_only = True)
		d = data.copy()
		d[d==0] = -1  # replace zeros in data with -1
		for i in top_matches:
			self.data_array[i] += d

	def read(self, address):
		top_matches = find_matches(self.addresses, address, self.nact, index_only = True)
		i = top_matches[0]
		sum = self.data_array[i].copy()
		for i in top_matches[1:]:
			sum += self.data_array[i]
		sum[sum<1] = 0   # replace values less than 1 with zero
		sum[sum>0] = 1   # replace values greater than 0 with 1
		return sum

def recall(prefix, env):
	# recall sequence starting with prefix
	# build address to start searching
	threshold = env.pvals["word_length"] * env.pvals["char_match_fraction"]
	b0 = env.cmap.char2bin(prefix[0])  # binary word associated with first character
	address = merge(b0, b0)
	for char in prefix[1:]:
		b = env.cmap.char2bin(char)
		address = merge(b, address)
	found = [ prefix, ]
	word2 = prefix
	# now read sequence using prefix address
	while True:
		b = env.sdm.read(address)
		top_matches = env.cmap.bin2char(b)
		found.append(top_matches)
		found_char = top_matches[0][0]
		if found_char == "#":
			# found stop char
			break
		# perform "cleanup" by getting b corresponding to top match 
		if top_matches[0][1] > 0:
			# was not an exact match.  Check to see if hamming distance larger than threshold
			if top_matches[0][1] > threshold:
				break
			# Cleanup by getting b corresponding to top match
			b = env.cmap.char2bin(found_char)
		address = merge(b, address)
		word2 += found_char
	return [found, word2]

def store_strings(env, strings):
	for string in strings:
		print("storing '%s'" % string)
		b0 = env.cmap.char2bin(string[0])  # binary word associated with first character
		address = merge(b0, b0)
		for char in string[1:]+"#":  # add stop character at end
			b = env.cmap.char2bin(char)
			env.sdm.store(address, b)   # store code for char using address prev_bin
			address = merge(b, address)

def store_param_strings(env):
	# store strings provided as parameters in command line (or updated)
	store_strings(env, env.pvals["string_to_store"])

def recall_strings(env, strings):
	# recall list of strings starting with first character of each
	error_count = 0
	for word in strings:
		print ("\nRecall '%s'" % word)
		found, word2 = recall(word[0], env)
		if word != word2:
			error_count += 1
			msg = "ERROR"
		else:
		    msg = "Match"
		pp.pprint(found)
		print ("Recall '%s'" % word)
		print("found: '%s' - %s" % (word2, msg))
	print("%s words, %s errors" % (len(strings), error_count))

def recall_param_strings(env):
	# recall stored sequences starting with first character
	recall_strings(env, env.pvals["string_to_store"])


def main():
	env = Env()
	store_param_strings(env)
	# retrieve sequences, starting with first character
	recall_param_strings(env)
	do_interactive_commands(env)

main()
