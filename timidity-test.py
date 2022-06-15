from timidity import Parser, play_notes
import numpy as np

ps = Parser("D:/dwn/inv1.mid")

play_notes(*ps.parse(), np.sin)