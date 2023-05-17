import math
import heapq
import hashlib
import random
from utils import pretty_print
import time
BLOCK_LENGTH = 2**14 # standard len


class DownloadHandler:
    def __init__(self, tracker, torrent):
        self.tracker = tracker
        self.needed_pieces = []
        self.pending_pieces = []
        self.finished_pieces = []
        # self.piece_list = [] # initializing our empty setup
        self.peer_piece_dict = {}
        self.torrent = torrent
        self.start_time = time.time()  # record the start time of the download
        self.total_size = torrent.tracker.length # total file size
        self.piece_list = [Piece(index, tracker, self) for index in range(tracker.num_pieces)]

        
    def init_pieces(self):
        piece_length = self.tracker.piece_length
        for piece_num in range(0, self.tracker.num_pieces):
            hash = self.tracker.pieces[(20 * piece_num) : (20 * piece_num) + 20]
            if piece_num < (self.tracker.blocks_per_piece - 1):
                piece = Piece(
                    hash, piece_length, self.tracker.blocks_per_piece, piece_num
                )
            else:
                last_piece_length = 0
                if self.tracker.length % piece_length > 0:
                    last_piece_length = self.tracker.length % piece_length
                else:
                    last_piece_length = self.tracker.piece_length
                num_blocks_per_last_piece = math.ceil(last_piece_length / 2**14)
                piece = Piece(
                    hash, last_piece_length, num_blocks_per_last_piece, piece_num
                )
            self.needed_pieces.append([piece, 0])
        random.shuffle(self.needed_pieces)

   
    def notfy_manager(self, index, peer):
        # first check if peer is in peers <-> piece dictionary
        if peer not in self.peer_piece_dict:
            # if not, add it
            self.peer_piece_dict[peer] = 1
        # if there
        else:
            self.peer_piece_dict[peer] += 1
                  
    # for avg download speed
    def format_size(self, size):
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit = 0
        while size >= 1024:
            size /= 1024
            unit += 1
        return f"{size:.2f}{units[unit]}"
    
    def get_avg_speed(self):
        elapsed_time = time.time() - self.start_time  # total time taken
        average_speed = self.total_size / elapsed_time  # calculate average speed in bytes/second
        return average_speed

    def next(self, pieces):
        if len(self.pending_pieces):
            return self.pending_pieces.pop(0)
        if len(self.needed_pieces) == 0:
            avg_speed = self.get_avg_speed()
            pretty_print("DOWNLOAD FINISHED 🥳🥳🥳", "green")
            pretty_print(f"Average download speed: {self.format_size(avg_speed)}/s", "green")
            self.torrent.complete = True
            return None
        filtered = [x for x in self.needed_pieces if x[0].index in pieces]
        if len(filtered) == 0:
            return None
        top = min(filtered, key=lambda x: x[1])
        self.needed_pieces.remove(top)
        return top[0]




class Piece:
    def __init__(self, index, tracker, download_handler):
        self.index = index
        self.tracker = tracker
        self.download_handler = download_handler
        self.num_blocks =  math.ceil(tracker.piece_length / BLOCK_LENGTH)
        if index != tracker.num_pieces - 1:
            self.piece_length = tracker.piece_length
        else:
            if tracker.length % tracker.piece_length != 0:
                self.piece_length = tracker.length % tracker.piece_length
            else:
                self.piece_length = tracker.piece_length
        self.block_list = [Block(i, tracker, self) for i in range(self.num_blocks)]
        
        



class Block:
    def __init__(self, index, tracker, piece):
        self.index = index
        self.piece = piece
        self.tracker = tracker
        if index != piece.num_blocks - 1:
            self.length = BLOCK_LENGTH
        else:
            if piece.piece_length % BLOCK_LENGTH != 0:
                self.length = piece.piece_length % BLOCK_LENGTH
            else:
                self.length = BLOCK_LENGTH
        self.offset = index * BLOCK_LENGTH
        
        
         


class FileWriter:
    def __init__(self, filename, torrent):
        self.filename = filename
        pretty_print(f"NAME OF FILE: {filename}", "green")

        self.total_size = torrent.tracker.length
        self.piece_length = torrent.tracker.piece_length
        self.file = open(filename, "wb")
        self.torrent = torrent
        self.pieces = [False for _ in range(-(-self.total_size // self.piece_length))]  # ceil division
                                                         # total_size // piece_length

    def write_block(self, piece_index, block_index, block_data):
        position = piece_index * self.piece_length + block_index
        self.file.seek(position)
        self.file.write(block_data)
        self.file.flush()
        self.pieces[piece_index] = True  # mark piece as downloaded
        
    def read_piece(self, index, begin, length):
        # Open the file in binary mode
        with open(self.filename, 'rb') as file:
            # Seek to the correct position in the file
            file.seek(index * self.piece_length + begin)

            # Read the requested data
            piece_data = file.read(length)

        return piece_data
    
    def get_bitfield(self):
        bitfield = bytearray()
        for i in range(0, len(self.pieces), 8):
            byte = 0
            for j in range(8):
                if i + j < len(self.pieces) and self.pieces[i + j]:
                    byte |= 1 << (7 - j)
            bitfield.append(byte)
        return bytes(bitfield)

    def close(self):
        self.file.close()
