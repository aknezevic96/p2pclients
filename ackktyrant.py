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

class AckkTyrant(Peer):
    def post_init(self):
        print ("post_init(): %s here!" % self.id)
        self.dummy_state = dict()
    
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

        requests = []   # We'll put all the things we want here
        # Symmetry breaking is good...
        random.shuffle(needed_pieces)
        pieceDict = {}
		
        
        # Sort peers by id.  This is probably not a useful sort, but other 
        # sorts might be useful
        peers.sort(key=lambda p: p.id)
        # request all available pieces from all peers!
        # (up to self.max_requests from each)
        for pr in peers:
            for a in pr.available_pieces:
                if a not in pieceDict:
                    pieceDict[a] = 1 #adds new piece to dict and sets frequency to 1
                else:
                    pieceDict[a] += 1 #incrememnts frequency of repeat piece by 1
		
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
            if n != len(isect):
                rare = []
                for p in isect:
                    rare.append((p, pieceDict[p]))
                    rare.sort(key=lambda l : l[1]) #rarest first 
                    reqPiece = [x[0] for x in rare[0:n]]
                for p in reqPiece:
                    start_block = self.pieces[p]
                    r = Request(self.id, peer.id, p, start_block)
                    requests.append(r)
			
            else:
                # aha! The peer has this piece! Request it.
                # which part of the piece do we need next?
                # (must get the next-needed blocks in order)
                for p in isect:
                    start_block = self.pieces[p]
                    r = Request(self.id, peer.id, p, start_block)
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
        # One could look at other stuff in the history too here.
        # For example, history.downloads[round-1] (if round != 0, of course)
        # has a list of Download objects for each Download to this peer in
        # the previous round.
		
        k = 3 #algorithm parameters
        alpha = 0.2
        gamma = 0.1
        # unchoke algorithm
        random.shuffle(requests)
        random.shuffle(peers)
        pid = [p.id for p in peers] #initialize
        d = [((self.conf.max_up_bw + self.conf.min_up_bw) / 2.0) / len(peers)] * len(peers)
        u = [((self.conf.max_up_bw + self.conf.min_up_bw) / 2.0) / k] * len(peers)
        
        if len(requests) == 0:
            chosen = []
            bws = []
        else:
            unchk = set([z.to_id for z in history.uploads[round-1]]) #find period unchokes
            if (round-2) >= 0:
                unchk1 = set([z.to_id for z in history.uploads[round-2]])
            else:
                unchk1 = []
            if (round-3) >= 0:
                unchk2 = set([z.to_id for z in history.uploads[round-3]])
            else:
                unchk2 = []
            
            dl = set([y.from_id for y in history.downloads[round-1]]) #download rate
            for unchked in unchk:
                i = pid.index(unchked)
                if unchked in unchk and unchked in unchk1 and unchked in unchk2: #unchoked for each previous period
                    u[i] *= (1-gamma)
                if unchked in dl:
                    dlrate = 0
                    for x in history.downloads[round-1]: #unchokes
                        if x.to_id == unchked:
                            dlrate += x.blocks
                            d[i] = dlrate
                        else:
                            u[i] *= (alpha+1) #did not unchoke
            up_bw = self.up_bw
            order = [float(a)/b for (a,b) in zip(d,u)]
            order = sorted(range(len(d)), key=lambda x: order[x]) #sort by decreasing ratio
            order = order[::-1]
            chosen = [] #initialize
            bws = []
            rqrs = [x.requester_id for x in requests] #get requesters
            i = 0
            while i < len(order) and up_bw >= u[i]: #search for proper ones
                if pid[i] in rqrs: #found
                    up_bw -= u[i] #set to max in swarm
                    chosen.append(pid[i])
                    bws.append(u[i]) #add to lists for uploading
                i += 1
		
		
            #request = random.choice(requests)
            #chosen = [request.requester_id]
            # Evenly "split" my upload bandwidth among the one chosen requester
            #bws = even_split(self.up_bw, len(chosen))

        # create actual uploads out of the list of peer ids and bandwidths
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]
            
        return uploads
