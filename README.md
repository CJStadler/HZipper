HZipper
=======

Compress text files using Huffman coding


Written for cs106 at Haverford College with Marco Alvarez.


hzipper.py command line interface:
	<[-c compress input] [-d decompress input] [-u compress url]> <input filename or url> <output filename>

	example usage:
		hzipper.py -c bigtest.doc compressed.hzip
		hzipper.py -u http://google.com google.hzip

BUGS:
information is lost in some contrived examples

TO DO:
finish hzipper1?