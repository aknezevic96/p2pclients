#!/usr/bin/python

# This is a dummy peer that just illustrates the available information your peers 
# have available.

# You'll want to copy this file to AgentNameXXX.py for various versions of XXX,
# probably get rid of the silly logging messages, and then add more logic.

import random
import logging

from messages import Upload, Request
from util import even_split
from peer import Peer

class AckkPropShare(Peer):
    def post_init(self):
        print ("post_init(): %s here!" % self.id)
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
    
    def requests(self, peers, history):
        """
        peers: available info about the peers (who has what pieces)
        history: what's happened so far as far as this peer can see

        returns: a list of Request() objects

        This will be called after update_pieces() with the most recent state.
        """
        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
        needed_pieces = filter(needed, range(len(self.pieces)))
        np_set = set(needed_pieces)  # sets support fast intersection ops.


##        logging.debug("%s here: still need pieces %s" % (
##            self.id, needed_pieces))
##
##        logging.debug("%s still here. Here are some peers:" % self.id)
##        for p in peers:
##            logging.debug("id: %s, available pieces: %s" % (p.id, p.available_pieces))
##
##        logging.debug("And look, I have my entire history available too:")
##        logging.debug("look at the AgentHistory class in history.py for details")
##        logging.debug(str(history))

        requests = []   # We'll put all the things we want here
        # Symmetry breaking is good...
        random.shuffle(needed_pieces)
        # Keep track of pieces and its frequency 
        availablePieces = {}
        for p in peers:
            for available_p in p.available_pieces:
                if not available_p in availablePieces:
                    availablePieces[available_p] = 1
                else:
                    availablePieces[available_p] += 1
        
               
        # Sort peers by id.  This is probably not a useful sort, but other 
        # sorts might be useful
        peers.sort(key=lambda p: p.id)
        # request all available pieces from all peers!
        # (up to self.max_requests from each)
        for peer in peers:
            av_set = set(peer.available_pieces)
            isect = av_set.intersection(np_set)
            n = min(self.max_requests, len(isect))
            # More symmetry breaking -- ask for random pieces.
            # This would be the place to try fancier piece-requesting strategies
            # to avoid getting the same thing from multiple peers at a time.
            if n == len(isect):
                for piece_id in isect:
                    # aha! The peer has all desired pieces! Request it.
                    start_block = self.pieces[piece_id]
                    r = Request(self.id, peer.id, piece_id, start_block)
                    requests.append(r)
            else:
                #get the least available desired pieces first
                
                least_available_pieces = []
                for piece_id in isect:
                    least_available_pieces.append((piece_id,availablePieces.get(piece_id)))
        
                least_available_pieces.sort(key=lambda x: x[1])
                request_pieces = [x[0] for x in least_available_pieces[:n]]

                for piece_id in request_pieces:
                    # aha! The peer has this piece! Request it.
                    start_block = self.pieces[piece_id]
                    r = Request(self.id, peer.id, piece_id, start_block)
                    requests.append(r)

        return requests

    def uploads(self, requests, peers, history):
        """
        requests -- a list of the requests for this peer for this round
        peers -- available info about all the peers
        history -- history for all previous rounds

        returns: list of Upload objects.

        In each round, this will be called after requests().
        """
        
        
        round = history.current_round()
        logging.debug("%s again.  It's round %d." % (
            self.id, round))
        # One could look at other stuff in the history too here.
        # For example, history.downloads[round-1] (if round != 0, of course)
        # has a list of Download objects for each Download to this peer in
        # the previous round.

        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
        else:
            logging.debug("Still here: uploading to a random peer")
            
            #Get a key, value(id,#recieved blocks from the peer) pair
            bloks_recieved = {}
            requester_list = [x.requester_id for x in requests]

            for br in history.downloads[round - 1]:
                if br.from_id not in bloks_recieved and br.from_id in requester_list:
                    bloks_recieved[br.from_id] = br.blocks
                elif br.from_id in requester_list:
                    bloks_recieved[br.from_id] += br.blocks

            chosen = []
            bws = []

            for peer in peers:
                #in previous round client recieved blocks from this peer 
                if peer.id in bloks_recieved:
                    #chose the peer
                    chosen.append(peer.id)
                    #calculate its bws
                    bws.append(int(0.9 * self.up_bw * bloks_recieved[peer.id]/sum(bloks_recieved.values())))
                                            

            #Now randomly choose last peer
            random.shuffle(peers)
            for peer in peers:
                if peer.id not in bloks_recieved:
                    #chose the peer
                    chosen.append(peer.id)
                    #calculate its bws
                    bws.append(self.up_bw - sum(bws))
                    
            
        # create actual uploads out of the list of peer ids and bandwidths
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]
            
        return uploads
