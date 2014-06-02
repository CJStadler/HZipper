"""
hzipper.py
Chris Stadler

Compresses and Decompresses text files using Huffman coding.

A zipped file has this format:
2 byte int x == # of bytes used by code tree (1byte could theoretically be too small).
x bytes storing preorder traversal of decoding tree
1 byte int r == number of bits used in the file's last byte (the rest of its bits will be 0).
    r < 8 so it only really needs 3 bits but I'm using a byte for simplicity.
n bytes storing a message of 8(n-1) + r bits
"""
import struct

# Main function for compressing a file or web page.
def hzip(readName, writeName, url=False):

    # Open files for reading and writing
    if url:
        import urllib2
        R = urllib2.urlopen(readName) # file-like object
    else:
        R = open(readName, 'rb')
    W = open(writeName, 'wb')
    
    # Build coding tree and write to file
    text = R.read()
    t = codeTree() # init tree
    t.buildTree(text) # Build a decoding tree for the text using the huffman algorithm.
    t.writeTree(W) # Write the tree to file (also writing its length (in bytes) as the first 2 bytes).
    CB = t.genCodeBook() # Make a codebook (dictionary) from the tree for easy coding

    # Encode message and write to file
    encoded = encode(text, CB) # Encode the text into a bitstring.
    W.write(struct.pack('<B',len(encoded)%8)) # Write 1byte == the number of bits we are using in the last byte.
    writeBits(encoded, W) # Write the encodeded bitstring to file.

    # print compression ratio
    if url:
        size1 = len(text) # number of bytes if stored as ascii.
    else:
        size1 = R.tell() # number of bytes read.
        #print size1, len(text)
        # R.tell() >= len(text)? relating to new lines? For some reason I can't replicate this anymore.
    size2 = W.tell() # number of bytes written
    ratio = 1.0 - float(size2)/float(size1)
    print "The compression ratio is", ratio
    
    R.close()
    W.close()


# Main function for decompressing a zipped file.
def unzip(readName, writeName):

    # Open files
    R = open(readName, 'rb')
    W = open(writeName, 'wb')

    # Generate decoding tree from file
    t = codeTree() #init
    t.readTree(R)

    # Decode using tree
    lastByteBits, = struct.unpack('<B', R.read(1)) # Read number of bits in last byte
    bits = readBits(R, remainder=lastByteBits) # Read bytes into bitstring
    text = decode(bits, t) # decode the bitstring
    W.write(text) # write the message to the output file

    R.close()
    W.close()

    
# Write booleans to file (f) as bits (True=1, False=0), 1 byte at a time.
def writeBits(bools, f):
    bits = 0 # keep track of how many bits of the current byte have been written
    byte = 0 # current byte
    i = 0
    while i < len(bools):
        byte = byte<<1 # bitshift by 1
        if bools[i]: # bit=1
            byte += 1
            # else keep the 0
        bits += 1
        i += 1
        if bits >= 8: # byte is full
            f.write(struct.pack('<B',byte)) # Write the byte to file
            byte = 0 # init next byte
            bits = 0 # restart count
        elif i == len(bools): # reached end of bitstring
            # Pad the last byte (with 0s)
            pad = 8 - bits
            byte = byte<<pad
            f.write(struct.pack('<B',byte)) # Write padded byte to file


# Returns the file (or the next n bytes) as a list of booleans.
def readBits(f, n=None, remainder=8):
    bools = [] # list of bits represented by booleans
    if n:
        data = f.read(n)
    else:
        data = f.read()
    # For each byte, read out its bits
    for c in data:
        byte, = struct.unpack('<B', c) # The byte as an int
        mask = 128 # a byte with a single 1 in the leftmost bit
        while mask > 0: # less than 8 shifts performed
            if byte & mask == mask: # the byte has a 1 in the same position as the mask
                bit = True
            else:
                bit = False
            bools += [bit]
            mask = mask>>1 # bitshift to the right by 1
    # Get rid of extra bits (not part of coded message) from last byte
    bools = bools[:len(bools)-8+remainder]

    return bools
        
# Encode the text string into bits.
def encode(text, codebook):
    bools = []
    for c in text:
        code = codebook[c]
        bools += code
    return bools

# Decode the bitstring into a text string.
def decode(bitstring, codeTree):
    string = ""
    x = codeTree.root # init current node
    for b in bitstring:
        if x.isLeaf(): # We've reached the end of a code word
            string += x.char
            x = codeTree.root # reset node
        if not x.isLeaf(): # this will only be violated if the root is a leaf.
            if b:
                x = x.right
            else:
                x = x.left
    if x.isLeaf(): # last bit
        string += x.char
    return string


class codeTree:
    def __init__(self):
        self.root = Node()

    # Methods to be accessed outside of class
    def writeTree(self, f): # Write the tree to file.
        bools = [] # bits representing tree
        self.traverse(self.root, bools) # Preorder traversal
        Nbytes = len(bools)/8 # number of bytes used to write the tree
        if len(bools)%8 != 0: # Finding ceiling...
            Nbytes += 1
        f.write(struct.pack('<H',Nbytes)) # Write the length of the tree to file
        writeBits(bools, f) # Write the encoding of the tree to file

    def readTree(self, f): # Construct the tree from its encoding.
        Nbytes, = struct.unpack('<H', f.read(2)) # Number of bytes used to encode tree
        treebits = readBits(f, Nbytes) # read the bytes for the tree
        self.root = self.treeFromTraversal(treebits) # Construct the tree

    def genCodeBook(self): # Make a codebook from the tree.
        CB = {}
        if self.root.isLeaf(): # This means there's only one char
            CB = {self.root.char: [True]} # just give it a code length 1
        else:
            self.recCB(self.root.left, [False], CB)
            self.recCB(self.root.right, [True], CB)
        return CB
        
    def buildTree(self,text): # Construct a decoding tree for a text.
        freqTable = self.genFreq(text) # Frequencies of every character in the text
        nodes = []
        # Make a node for each character, list them by frequency
        for c in freqTable:
            node = Node(freq=freqTable[c],char=c)
            self.insertByFreq(node,nodes)
        self.recHuffAlgorithm(nodes) # Constructs a tree from the nodes
        self.root = nodes[0]


    # Methods only needing to be accessed inside the class
    def treeFromTraversal(self, bits): # recursively build tree from the encoded preorder traversal.
        bit = bits.pop(0)
        if bit: # at leaf
            # make a byte from the next 8 bits
            byte = 0
            i = 0
            while i<8:
                byte = byte<<1
                if bits.pop(0):
                    byte += 1
                i += 1
            c = struct.pack('<B',byte) # Translate byte into character
            return Node(char=c)
        else: # at internal node
            l = self.treeFromTraversal(bits)
            r = self.treeFromTraversal(bits)
            return Node(left=l, right=r)
        
    def genFreq(self, text): # Generate a dictionary for every character in text: {character:frequency}
        freqTable = {}
        for c in text:
            if c in freqTable:
                freqTable[c] += 1
            else: # First instance of the character
                freqTable[c] = 1
        return freqTable

    def traverse(self, x, toWrite): # Recursively preorder traverse the tree, encoding as list of bools. 
        # x = current node
        # toWrite = encoding of tree
        if x.isLeaf():
            toWrite.append(True) # mark as leaf
            c = x.char
            # unpack char byte into bools
            byte, = struct.unpack('<B', c) # returns a single tuple
            mask = 128
            while mask > 0:
                bit = byte & mask == mask
                toWrite.append(bit)
                mask = mask>>1
        else:
            toWrite.append(False)
            self.traverse(x.left, toWrite)
            self.traverse(x.right, toWrite)
            
    def recCB(self, x, path, CB): # Traverse tree to construct codebook.
        # x = current node
        # path = path from root to x
        # CB = codebook
        if x.isLeaf():
            CB[x.char] = path # add code for c
        else:
            self.recCB(x.left, path+[False], CB)
            self.recCB(x.right, path+[True], CB)

    def recHuffAlgorithm(self,nodes): # Link a list of nodes sorted by freq into a decoding tree.
        if len(nodes) < 2:
            return # leave the root
        else: # combine two smallest nodes
            min1 = nodes.pop(0)
            min2 = nodes.pop(0)
            new = Node(left=min1, right=min2)
            new.freq = min1.freq + min2.freq
            self.insertByFreq(new,nodes) # insert the new node into the list

            self.recHuffAlgorithm(nodes)

    def insertByFreq(self,x,nodes): # Insert node x, keeping the list sorted by frequency.
        i = 0
        while i < len(nodes) and x.freq > nodes[i].freq:
                i += 1
        nodes.insert(i,x)
            

class Node:
    def __init__(self, freq=None, left=None, right=None, char=None): # Or init these to None?
        self.char = char
        self.freq = freq
        self.left = left
        self.right = right

    def isLeaf(self):
        return self.left == None and self.right == None

####### Command Line Interface ########
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Zip and unzip using Huffman coding")
    parser.add_argument('--compress', '-c', help='File to compress')
    parser.add_argument('--decompress', '-d', help='File to decompress')
    parser.add_argument('--url_compress', '-u', help='URL to compress')
    parser.add_argument('output', help='Name of file to write')
    args = parser.parse_args()
    if args.compress:
        hzip(args.compress,args.output)
    elif args.decompress:
        unzip(args.decompress,args.output)
    elif args.url_compress:
        hzip(args.url_compress, args.output, url=True)

###### TESTING ######
##fW = open('file.txt', 'wb')
##compress("hohehohooeh", {'h':[True,False], 'e':[True,True], 'o': [False]}, fW)
##fW.close()
##fR = open('file.txt', 'rb')
##print readBits(fR)
##codeTree = codeTree()
##codeTree.root.left = Node(char = 'o')
##codeTree.root.right = Node(left=Node(char='h'),right=Node(char='e'))
##print decompress(readBits(fR),codeTree)
##fR.close()
##########################
##f = genFreq("aaabbcaaabbcd")
##t = codeTree()
##t.buildTree(f)
##CB = t.genCodeBook()
##print CB
##########################
##inText = 'test.txt'
##f = open('test2.txt', 'w')
##f.write('ab')
##f.close()
##zipped = 'testZip.txt'
##outText = 'unzipped.txt'
##hzip(inText, zipped)
##unzip(zipped, outText)
##########################
#hzip('test2.txt', 'zipped.txt')

