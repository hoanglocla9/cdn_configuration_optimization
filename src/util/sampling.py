import random

class Sampling:
    def __init__(self, sampleRate):
        self.sampleRate = sampleRate
        
        
class ReservoirSampling(Sampling):
    def __init__(self,sampleRate):
        Sampling.__init__(self, sampleRate)
        
    def sample(self, contentIdList):
        result = []
        N = len(contentIdList)
        n = int(N * self.sampleRate * 1.0)
        if n > N:
            print("Sampling parameter error !!!")
            return None

        for i in range(n):
            result.append(contentIdList[i]) 

        for i in range(n, N):
            j = random.randint(0, i-1)
            if j < n:
                result[j] = contentIdList[i]
        return result

