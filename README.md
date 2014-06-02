HZipper
=======

Compresses and Decompresses text files using Huffman coding.

A zipped file has this format:
	2 byte int x == # of bytes used by code tree (1byte could theoretically be too small).
	x bytes storing preorder traversal of decoding tree
	1 byte int r == number of bits used in the file's last byte (the rest of its bits will be 0).
	    r < 8 so it only really needs 3 bits but I'm using a byte for simplicity.
	n bytes storing a message of 8(n-1) + r bits

Achieves a compression ratio of ~30-40%, although this is highly dependent on the language and document size. 

Written for cs106 at Haverford College with Marco Alvarez.


hzipper.py command line interface:
	<[-c compress input] [-d decompress input] [-u compress url]> <input filename or url> <output filename>

	example usage:
		hzipper.py -c bigtest.doc compressed.hzip
		hzipper.py -u http://google.com google.hzip

BUGS:
information is lost in some contrived examples

TO DO:
finish hzipper_new.py?