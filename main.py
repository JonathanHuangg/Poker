import random
from enum import Enum 

class GameStatus(Enum):
    PRE_FLOP = 1,
    FLOP = 2,
    TURN = 3,
    RIVER = 4,
    SHOWDOWN = 5,
    RESET = 6,

NUM_CARDS = 52
SUITS = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
DECK = [(rank, suit) for rank in RANKS for suit in SUITS]

class Poker:
    
    def __init__(self):
        self.hand = []
        self.opponent = []
        self.cards_out = []
        self.deck = DECK.copy()
        random.shuffle(self.deck)

        self.play_game()

    def play_game(self):
        curr_status = GameStatus.PRE_FLOP

        while(True):
            
            if curr_status == GameStatus.PRE_FLOP:
                print()
                print("NEW GAME")
                print()
                self.hand = self.build_cards()
                self.opponent = self.build_cards()
                
                print(self.hand)
                print(self.opponent)
                # insert logic here later for betting

                if input("next? ") == "n":
                    curr_status = GameStatus.FLOP

            elif curr_status == GameStatus.FLOP:
                self.cards_out = self.build_cards(3)
                print("first 3 cards: ", self.cards_out)

                # insert logic here for betting
                if input("next? ") == "n":
                    curr_status = GameStatus.TURN

            elif curr_status == GameStatus.TURN:
                self.cards_out.append(self.build_cards(1)[0])
                print("First 4 cards: ", self.cards_out)
                # insert logic here for betting

                if input("next? ") == "n":
                    curr_status = GameStatus.RIVER
            elif curr_status == GameStatus.RIVER:
                self.cards_out.append(self.build_cards(1)[0])
                print("First 5 cards: ", self.cards_out)
                # insert logic here for betting

                if input("next? ") == "n":
                    curr_status = GameStatus.SHOWDOWN 
            elif curr_status == GameStatus.SHOWDOWN:
                print(self.hand)
                print(self.opponent)

                # figure out winner
                if input("next? ") == "n":
                    curr_status = GameStatus.RESET 

            elif curr_status == GameStatus.RESET:
                yn = input("Play again? Enter y or n ")
                if (yn in ["y", "Y", "yes", "YES"]):
                    self.hand = []
                    self.opponent = []
                    self.cards_out = []
                    self.deck = DECK.copy()
                    random.shuffle(self.deck)
                    curr_status = GameStatus.PRE_FLOP
                else:
                    return  
    
    def build_cards(self, n=2):
        hand = []
        for _ in range(n):
            card = self.deck.pop()
            hand.append(card[0] + " " + card[1])
        return hand
    
     
poker = Poker()