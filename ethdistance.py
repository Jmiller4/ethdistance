from etherscan_py import etherscan_py
# etherscan-py is a python wrapper for the Etherscan API
# docs: https://pypi.org/project/etherscan-py/
import time


class transaction_tree():
  # a tree object to store information about wallets and their shared transactions.
  # as we do breadth first search through the list of ethereum transactions, we build up this tree via expand().
  # path_to_root() gives the path of wallets connecting a leaf to the root, along with the transaction hashes proving that each link exists.

  def __init__(self, root_wallet):

    self.root_wallet = root_wallet # self.root_wallet is the wallet at the "base" of the tree.

    self.parent_info = dict() # parent_info is a dict mapping wallets to (wallet, transaction hash) pairs
                              # example: parent_info[A] = (B, X) means that A's parent in the tree is B, and A & B interacted via the transaction with hash X

    self.observed_wallets = set([root_wallet]) # we'll keep track of all the wallets we've seen to make sure that the tree stays a tree.

    self.leaves = set([root_wallet]) # we'll keep track of all the leaves in the tree (wallets with only one link to the rest of the tree)


  def expand(self, parent_wallet, child_wallet, tx_hash):
    # a function to add a new leaf to the tree

    # error checking to make sure we don't create a cycle
    assert parent_wallet in self.observed_wallets
    assert child_wallet not in self.observed_wallets

    # add the information about the new link to parent_info
    self.parent_info[child_wallet] = (parent_wallet, tx_hash)

    # update the set of observed wallets
    self.observed_wallets.add(child_wallet)

    # update our set of leaves
    self.leaves.discard(parent_wallet)
    self.leaves.add(child_wallet)


  def path_to_root(self, wallet):
    # this function returns two lists.
    # the first list is a list of wallets: in this list, the first element is the wallet given as input and the last element is the root wallet.
    # the second list contains the transaction hashes that connect each adjacent pair of wallets from the first list.
    # so, if the first list has n wallets, the second list will have n-1 transaction hashes.

    # check to make sure a path actually exists, if not throw an error
    assert wallet in self.observed_wallets

    # the function is recursive. sometimes recursive functions use a lot of memory/ time, but this one is linear in the length of the path.
    # this is the base case.
    if wallet == self.root_wallet:
      return [self.root_wallet], []

    # else, recurse to find the rest of the path starting from the current wallet.
    parent = self.parent_info[wallet][0]
    tx = self.parent_info[wallet][1]

    partial_path_to_root, partial_txs_to_root = self.path_to_root(parent)

    return [wallet] + partial_path_to_root, [tx] + partial_txs_to_root


def neighbor_address(etherscan_tx, wallet):
    # we link wallets together if they were partners in a transaction, but we don't really care who was sending vs receiving.
    # so, given an Etherscantransaction object and one of the wallets in the transaction, this function gets the other wallet.

    if etherscan_tx.from_address.lower() == wallet.lower():
      return etherscan_tx.to_address
    return etherscan_tx.from_address

def shortest_path(source_wallet, target_wallet, API_key, max_depth=3, free_API_key=True):
  # this function tries to find a shortest path by doing a breadth-first search out from source_wallet,
  # stopping when it finds target_wallet or exhausts all wallets at its max depth.
  # it has the potential to use a very large amount of time and memory if max_depth is set too high.

  # first, initialize a client for the etherscan API
  client = etherscan_py.Client(API_key)
  
  # second, cast wallet addresses to lowercase (since these addresses are base 16 numbers, this should be fine)

  source_wallet = source_wallet.lower()
  target_wallet = target_wallet.lower()

  tree = transaction_tree(source_wallet)
  # create a queue of (wallet, depth) pairs to look through. Here depth = the depth at which we found this particular wallet.
  queue = [(source_wallet, 0)]

  while len(queue) >= 1:
    wallet_depth_pair = queue.pop(0)

    wallet = wallet_depth_pair[0]
    depth  = wallet_depth_pair[1]

    # go through all the transactions this wallet has been involved in.
    # but first, if we have a free API key, we need to wait 1 second before calling the API, or else we'll get an error. Sad!
    if free_API_key: time.sleep(1)
    for tx in client.get_all_transactions(wallet, 1):

      # for each transaction, check out the other wallet (and cast the wallet address to lowercase)
      # and add it to the tree if we haven't seen it before.

      new_wallet = neighbor_address(tx, wallet).lower()
      if new_wallet not in tree.observed_wallets and new_wallet != '':
        tree.expand(wallet, new_wallet, tx.txhash)

      # if we found the wallet we're looking for, we're done
      if new_wallet == target_wallet:
        return tree.path_to_root(new_wallet)

      # else, if we're not already at max depth, add the new wallet to the queue
      # so that we can search through its neighbors.
      if depth < max_depth:
        queue.append((new_wallet, depth + 1))

  # if we exhaust the queue and still haven't found the wallet, return False
  return False

