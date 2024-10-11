import numpy as np
import scipy.special
from scipy.special import logsumexp
from scipy.stats import skew, kurtosis

__version__ = "1.0.3"
def compute_bimodality(data):
    """
    Compute bimodality of a dataset.
    
    Args:
    - data: A 1D numpy array or list containing the dataset.
    
    Returns:
    - bimodality: BC =\frac{(s^2 + 1)}{k+\frac{3(N-1)^2)}{(N-2)(N-3)}}
    """
    # Compute skewness and kurtosis
    s = skew(data)
    k = kurtosis(data)
    N = len(data)
    BC = (s*s + 1) / (k + 3 * (N-1)*(N-1)/(N-2)/(N-3))
    return BC
        
def find_threshold(bins,alpha,rate,pi):
    min_value = bins[0]
    max_value = bins[-1]
    g = (np.power(rate, alpha)/scipy.special.gamma(alpha)) * np.power.outer(bins, alpha-1) *  np.exp(-np.multiply.outer(bins, rate))
    gall = g[:,0] * pi[0] + g[:,1] * pi[1] # histogram of the bimodal distribution
    minima = float('inf')
    minima_index = None
    # Iterate through histogram values
    if(max_value == min_value):
        return 0
    mode1 = int((alpha[0] -1) / rate[0] * 1000 / (max_value-min_value))
    mode2 = int((alpha[1] - 1) / rate[1]* 1000 / (max_value-min_value))
    #print((alpha -1) / rate,mode1,mode2)
    start = np.max([1,np.min([mode1,mode2])])
    end = np.min([999,max([mode1,mode2])])
   ## for i in range(start, end):
    #    if gall[i] < gall[i-1] and gall[i] < gall[i+1]:
            # Current value is smaller than both neighbors, potential minima
    #        if gall[i] < minima:
     #           minima = gall[i]
      #          minima_index = i
    g_diff = abs(g[:,0] * pi[0] - g[:,1] * pi[1])
    min_index = np.argmin(g_diff[start:end])
    return min_index + start
        
def invpsi(y):
    """
    Inverse digamma (psi) function.  The digamma function is the
    derivative of the log gamma function.
    """
    # Adapted from matlab code in PMTK (https://code.google.com/p/pmtk3), copyright
    # Kevin Murphy and available under the MIT license.
 
    # Newton iteration to solve digamma(x)-y = 0
    x = np.exp(y) + 0.5
    mask = y < -2.22
    x[mask] = 1.0 / (y[mask] - scipy.special.psi(1))
 
    # never more than 5 iterations required
    for i in range(5):
        x = x - (scipy.special.psi(x)-y) / scipy.special.polygamma(1, x)
    return x


def fit(x, alpha, rate, pi,k=3):
    """alpha and rate are user specified parameters to be fitted
    pi is fixed at the current implementation"""
    #alpha = 10*np.random.rand(k)
    #rate = 10*np.random.rand(k)
    
    log_x = np.log(x)
 
    for i in range(100):
        # log probability of each data point in each component
        logg = alpha*np.log(rate) - scipy.special.gammaln(alpha) + \
            np.multiply.outer(log_x, alpha-1) - np.multiply.outer(x, rate)
        logp = np.log(pi) + logg - logsumexp(logg, axis=1, b=pi[np.newaxis])[:, np.newaxis]
        p = np.exp(logp)

        # new mixing weights
        #pi = np.mean(np.exp(logp), axis=0)

        # new rate and scale parameters
        A = np.einsum('i,ij->j', log_x, p)
        B = np.einsum('j,ij->j', np.log(rate), p)
        alpha_argument = (A + B) / np.sum(p, axis=0)
        rate = alpha*np.sum(p, axis=0) / np.einsum('i,ij->j', x, p)
        # when the fit is bad (early iterations), this conditional maximum
        # likelihood update step is not guarenteed to keep alpha positive,
        # which causes the next iteration to be unavailable.
        alpha = np.maximum(invpsi(alpha_argument), 1e-8)


    #x = np.linspace(0.001, np.max(x), 1000)
    #g = (np.power(rate, alpha)/scipy.special.gamma(alpha)) * np.power.outer(x, alpha-1) *  np.exp(-np.multiply.outer(x, rate))
    #ax2 = pp.gca().twinx()
    #ax2.plot(x, g[:, 0])
    #ax2.plot(x, g[:, 1])
    return (alpha,rate,pi)