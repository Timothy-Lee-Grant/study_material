
# 26 Jul 2026
'''
Two children, Lily and Ron, want to share a chocolate bar. Each of the squares has an integer on it.

Lily decides to share a contiguous segment of the bar selected such that:

The length of the segment matches Ron's birth month, and,
The sum of the integers on the squares is equal to his birth day.
Determine how many ways she can divide the chocolate.

Example



Lily wants to find segments summing to Ron's birth day,  with a length equalling his birth month, . In this case, there are two segments meeting her criteria:  and .

Function Description

Complete the birthday function in the editor below.

birthday has the following parameter(s):

int s[n]: the numbers on each of the squares of chocolate
int d: Ron's birth day
int m: Ron's birth month
Returns

int: the number of ways the bar can be divided
Input Format

The first line contains an integer , the number of squares in the chocolate bar.
The second line contains  space-separated integers , the numbers on the chocolate squares where .
The third line contains two space-separated integers,  and , Ron's birth day and his birth month.
'''

def birthday(s, d, m):
    # Write your code here
    length = m
    targetSum = d
    lengthS = len(s)
    windowSum = 0
    ways = 0
    for i in range(length):
        if i >= lengthS:
            return None
        windowSum += s[i]
    
    #Now my window is built
    i = m-1
    while i < lengthS:
        if windowSum == targetSum:
            ways += 1
        windowSum += s[i]
        windowSum -+ s[i-(m-1)]
        i += 1
    return ways

if __name__ == '__main__':
    fptr = open(os.environ['OUTPUT_PATH'], 'w')

    n = int(input().strip())

    s = list(map(int, input().rstrip().split()))

    first_multiple_input = input().rstrip().split()

    d = int(first_multiple_input[0])

    m = int(first_multiple_input[1])

    result = birthday(s, d, m)

    fptr.write(str(result) + '\n')

    fptr.close()


# second attempt

def birthday(s, d, m):
    # Write your code here
    length = m
    targetSum = d
    lengthS = len(s)
    windowSum = 0
    ways = 0
    for i in range(length):
        if i >= lengthS:
            return None
        windowSum += s[i]
        
    #check the first one
    if windowSum == targetSum:
        ways += 1
    
    # loop through each of the windows
    #I need to ask myself, why is it that I actually need to build the first one outside of the loop and then go into the loop
    
    # I want i to be at the last place that my window is at, then add one
    #length (but non-inclusive) so it did NOT run that one, so this is what I want
    i = length 
    while i < lengthS:
        #Now I am on a new one (but within the valid array index)
        windowSum += s[i]
        # I want to kick off the last element which is no longer valid. How can I do this? I am currently at i and I want d elements i-d (what will this do, and what will happen because of the idea of 1 indexed and 0 indexed?) 
        # I am currently at i and I want to ask, how many steps backward should I take? but I am currently at i, so taking 0 steps is actually meaning that I am having one element? that does not seem right..... but if I take d steps, then if d is 1, I will be at the index of the element that I want to kick off if I take d steps. (I guess if d=0, then I would kick that eleemnt off itself and it would be 0 elements, so it might be right). So I need to think of it as d means the element which I want to kick off
        windowSum -= s[i-(d)]
        
        #now I should see if there is another valid
        if windowSum == targetSum:
            ways += 1
        i += 1
    
    return ways
    

    class Solution:
    def reverse(self, x: int) -> int:
        negative = false if x>=0 else true

        # take the first number of x, (or maybe I should take the last digit)
        x = abs(x)
        answer = 0
        tens_multiple = 1
        while x:
            last_num = x % 10
            x = x // 10

            # Now how can I put it at the start?
            #answer = (answer*10) + 
            
            # The number I just got will need to be placed at the top. So I need a way to know which 10s place to put it
            answer = (last_num * tens_multiple) + answer
            tens_multiple *= 10

        return answer if not negative else -answer
    

# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def rotateRight(self, head: Optional[ListNode], k: int) -> Optional[ListNode]:
        # To do this I see that I will need to have the kth element from the last become the new last.
        # This means that I will need to use that two pointers method where I make the 'fast' be ahead by k units. Then I can land at the node that I want to make the last node.
        # What will it look like to make that swap? I will want to have the element that it is pointing to be the new head, then I want to change the previously last element to point to the old head

        origional_head = head
        # I am just realizing that it is possible that we want to rotate more times than nodes that we have, but at this point I don't know the length of the linked list.
        curr = head
        length_of_ll = 0
        origional_end = None
        while curr:
            length_of_ll += 1
            origional_end = curr
            curr = curr.next

        k = k % length_of_ll
        # k is less than the length
        steps = 0
        fast = head
        slow = head
        while steps < k:
            steps += 1
            fast = fast.next
        
        while fast:
            fast = fast.next
            slow = slow.next
        
        new_head = slow.next
        slow.next = None
        origional_end.next = origional_head
        head = new_head
        return head



# 29 Aug 2026    
class Solution:
    def longestCommonSubsequence(self, text1: str, text2: str) -> int:
        #attempting to do this using brute force backtracking
        result = 0
        lenText2 = len(text2)

        #trying to think of what the recursive function should take as a parameter. Ususally the recursive functions take in the state of the system. But in this problem there are two disconnected structures. So does the state of the system represent the index of both?
        def traverse(t1i, t2i, currentLength):
            #What should the base case be? I am thinking that it should be when we are invalid, this would be if the indexes are outside of the bounds, or if they don't match. (actually if they don't match, then they should chose to not include, therefore it should be only when outside of the bounds)
            if t2i >= lenText2:
                return currentLength # I will want to return the number found, right? So now we have to think about how we accumulate the internal result as we are going through our options. I guess I can add this as another parameter that I just pass in.
            if text2[t2i] != text1[t1i]:
                #choose to not include it
                return traverse(t1i, t2i+1, currentLength) #t2 is the text that we are searching over during the backtracking process, so I should be moving this one and checking this one for when it get to over the bounds of the array
            
            # at this point I have found a match, I can choose to include it or not to include it. (is there any advantage to not including it? I cant think of an advantage because we are saying order, so wouldn't it always be best to include the highest recient item?)
            return traverse(t1i, t2i+1, currentLength+1)
        
        for index in range(len(text1)):
            res = traverse(index, 0, 0)
            result = max(res, result)
        return result

# attempt 2 with hint
class Solution:
    def longestCommonSubsequence(self, text1: str, text2: str) -> int:
        #I got a hint, and I saw that it told me to do a 2d decision matrix

        # The hint told me that I need to advance both at the same time, and so right now I am trying to think about how this problem teaches me: 1. What a 2d decision matrix is., and for what kind of problems they might be useful for. 2. How to traverse a structure with independent and disconnected structures. 3. It seems to be breaking these actions out, where as in my last attempt, I was doing a for loop for each index and then for every index in the text1 I was doing an operator of the recursive. 

        # I know that I saw something in the hint (before I decided to look away and attempt to implement it here myself) which was 1+recurse(text1), 1+recurse(text2)

        # High level, my goal is to see how many letters can match and disregard letters in the middle of the strings which I want to discard. This would mean that I want to go through both strings (structures), then for each of them (but because we have two strucures, how can I do this operation of 'go through the strucutre' because it is not one sigular strucure....). 
        def recurse():
            pass
        i1 = i2 = 0
        lenT1 = len(text1)
        lenT2 = len(text2)
        while i1 <= lenT1 and i2 <= lenT2:
            # I should be now able to somehow use this recursive thing which I saw in the hint to decide. But that will be if they do match? I also need to think about if they don't match, in that case do I move the t1 or t2? This two structure thing is really causing problems.....

        # at this point, I have finished going through all of the index values in either text 1 or text 2. But actually this means that I am done because even if there is other indexes left in the other text, there can not be any more matches because the other text is completely exausted. Therefore I can just return 'the result'
        return .

# attempt 3 (just annotating the copied solution)
class Solution:
    def longestCommonSubsequence(self, text1: str, text2: str) -> int:
        # Here is the answer copied. I will annotate it with my comments to try to understand it.

        # Once again I need to think of and study 'what does state actually mean?'. These backtracking and recursive problems always have the parameters as the state, and I know intellectually that the definition of state means that it fully describes the system. But I absolutely don't have a intuitive understanding for that. I also need to start thinking about the promises which a recursive function will give. Maybe I can almost think of it as a c# service interface. I can ask myself, 'for this state what is promised by it to give back to me as a result?'. I am also seeing that in this problem, the value which we are having is more of an emergant property.... 
        def backtrack(i, j):
            # Immediately I am wondering why we return 0 here. I always think of these recursive patterns where we return a number, or a 'builded object' back up the chain. So normally we will have some kind of variable which is like a collection (or an int) which I will then decided to mutate by adding items to it and then at the base case I can return that builder item back up the chain, and then at the layer above me I can decide which option to take. But this is different. I think it is because we are using this 1+bt() pattern.
            if i >= len(text1) or j >= len(text2):
                return 0
            
            # If we find a match, I will move both indexes and continue to recurse down and now I am saying whatever you give me bt(state) I will take that promise that you will return 'the answer' for that state, and I will add 1 to it. So I am passing in the next state with the indexes moved and I am asking a question about that next state, and then I am going to say for myself (the state which I am going to give back, it is 1 more than this).
            # The next question to investigate for understanding is how this value will emergently emerge and travel up correctly through the backtracking system. I see that I am returning one of three items for each bt(state). I can return 0, +1 of the next state, or the max of the next states. So the only time an increase occurs is when I find a match, and move both index. That makes sense. Then how does it accumulate through the system? I guess there will be multiple times that we hit a match and each time it will increase by one. 
            if text1[i] == text2[j]:
                return 1 + backtrack(i + 1, j + 1)
            
            #This actually answers my previous question about 'how do I know if I want to move index 1 or index 2?' the answer is that I actually try both! The way that I do this is by invoking bt on both the moving forward of index 1 (and keeping index 2 still), and then keeping index 1 still but advancing index 2.
            return max(backtrack(i + 1, j), backtrack(i, j + 1))
        
        return backtrack(0, 0)

# Next attempt
class Solution:
    def longestCommonSubsequence(self, text1: str, text2: str) -> int:
        # I deleted the problem and am now going to try to do it myself. Now, obviously, because I have seen it and annotated it extensively with comments, it is 100% fresh in my mind, and so this doesn't mean that I understand the problem fully, but it gives me another opportunity to try to instill it into my head. And also, I'm going to now be trying to turn this into a dynamic programming problem because I know, due to the hint, that it will have dynamic programming properties, so I will try to implement that as well.
        # So now I'm trying to think about how I can take this and model it into a decision tree, which is what Gemini told me in the hint. The way that I'm thinking about this is that state for the backtracking fully describes the system, and I have two parameters. Therefore, this means that I'm able to do a two-dimensional matrix. Now, that two-dimensional matrix will be able to have a value added. So actually, there are three variables that are going on. Now, this might be also a point of confusion within myself because I'm now looking at this and saying that there are three variables, but my state only has two. And maybe that's why in the past I was confused on this point? 
        # I know that in dynamic programming, I am going to be trying to save my state. And I know that because I have two variables that indicate my state, I am able to create a two-dimensional matrix, and that matrix is going to be able to tell me if I've already found a value. Now, what I'm thinking about doing is having all negative ones in my matrix, because that would mean that it is uninitialized, because there can never be a negative number. So, I know that if I see a negative one, that it hasn't been initialized yet. Then, what I can do is I am able to check to see if that target is filled out yet. And what I mean by target is the two index pairs that target on my two-dimensional matrix, and see if that value is set or not. If it is set, then all I need to do is return that, because I have already calculated that it is the best solution for that state.

        # Now it's time to finally think about how to introduce this two-dimensional matrix. I know that I need to actually create this two-dimensional matrix, and then we'll be able to put it right into our system.
        # Let's think about how we actually do this two-dimensional creation because this is something that always trips me up. And I know that Python has this weird syntax for actually how to go through a loop and then gives you back an item. Normally 'for i in range(...)' and then below I will have my logic which I can use that i variable. But then python allows semething where it is a value at the front. 
        # I had to look up an example of the syntax online and it was called list comprehension and it says that it is a shorthand and clean way of filtering and creating a new list from an existing list. The normal variable which I can normally interact with is going to be the name of the same thing which I am allowed to manipulate when I am doing the logic in front. So, what am I trying to do in this situation? I have a two-dimensional matrix which I am trying to create, and this means that for each of the rows, I am going to want to create a whole new list which has column number of elements in it, and each of the elements within the column are going to be -1. So now let me think about how I will do this. I can do a for loop which will give me the index of each of the rows that I want, and for each row, I am going to have a list. Now within that list again, I can do this exact same trick and have column inside of it, but now I put a -1.
        answer_pad = [ [ -1 for j in range(len(text2))] for i in range(len(text1))]

        def recurse(i, j):
            # Base Case: If I am outside of the bounds, then I can stop recursing and give back my promised answer. What is my promised answer? It should be 'for this state, how many subsequence matches are with in these two strings?' and the answer will be 0 because we are invalid!
            if i >= len(text1) or j >= len(text2): # is it actually a problem to do len here? Normally I always force them to be defined as integers, it seems like this would actually increase the time complexity. But Gemini always gives me the answer where len is taken here. So maybe there is something that I am missing that it doesn't negatively impact the time complexity?
                return 0
            
            # Here is where I will check if we have already calculated it yet.
            if answer_pad[i][j] != -1:
                return answer_pad[i][j]

            # They match: In the case that the items match, then I know that I want to move the index on both of them and then ask the question, "All right, for this new state, which is both of them increased, what is your answer?"
            return 1 + recurse(i+1, j+1)

            # They don't match: Now in the case that they do not match, I need to make the decision on if I am going to move the first index or the second index. Now I want to actually do both. And so what I'm going to do is I am going to ask that question for both cases. This means that I'm going to move the index of one and keep the other one still and say, "What is your answer?" And then I'm going to do the opposite for the other index and ask what that answer is. And then, because I'm trying to maximize it, I just say that I'm going to take the maximum of both of those.
            return max(recurse(i+1, j), recurse(i, j+1))
        
        return recurse(0,0)

# Previous solution failed. Copy and pasted it into gemini and it told me that I had the two errors. Fixed them now it passes.
class Solution:
    def longestCommonSubsequence(self, text1: str, text2: str) -> int:
        # I deleted the problem and am now going to try to do it myself. Now, obviously, because I have seen it and annotated it extensively with comments, it is 100% fresh in my mind, and so this doesn't mean that I understand the problem fully, but it gives me another opportunity to try to instill it into my head. And also, I'm going to now be trying to turn this into a dynamic programming problem because I know, due to the hint, that it will have dynamic programming properties, so I will try to implement that as well.
        # So now I'm trying to think about how I can take this and model it into a decision tree, which is what Gemini told me in the hint. The way that I'm thinking about this is that state for the backtracking fully describes the system, and I have two parameters. Therefore, this means that I'm able to do a two-dimensional matrix. Now, that two-dimensional matrix will be able to have a value added. So actually, there are three variables that are going on. Now, this might be also a point of confusion within myself because I'm now looking at this and saying that there are three variables, but my state only has two. And maybe that's why in the past I was confused on this point? 
        # I know that in dynamic programming, I am going to be trying to save my state. And I know that because I have two variables that indicate my state, I am able to create a two-dimensional matrix, and that matrix is going to be able to tell me if I've already found a value. Now, what I'm thinking about doing is having all negative ones in my matrix, because that would mean that it is uninitialized, because there can never be a negative number. So, I know that if I see a negative one, that it hasn't been initialized yet. Then, what I can do is I am able to check to see if that target is filled out yet. And what I mean by target is the two index pairs that target on my two-dimensional matrix, and see if that value is set or not. If it is set, then all I need to do is return that, because I have already calculated that it is the best solution for that state.

        # Now it's time to finally think about how to introduce this two-dimensional matrix. I know that I need to actually create this two-dimensional matrix, and then we'll be able to put it right into our system.
        # Let's think about how we actually do this two-dimensional creation because this is something that always trips me up. And I know that Python has this weird syntax for actually how to go through a loop and then gives you back an item. Normally 'for i in range(...)' and then below I will have my logic which I can use that i variable. But then python allows semething where it is a value at the front. 
        # I had to look up an example of the syntax online and it was called list comprehension and it says that it is a shorthand and clean way of filtering and creating a new list from an existing list. The normal variable which I can normally interact with is going to be the name of the same thing which I am allowed to manipulate when I am doing the logic in front. So, what am I trying to do in this situation? I have a two-dimensional matrix which I am trying to create, and this means that for each of the rows, I am going to want to create a whole new list which has column number of elements in it, and each of the elements within the column are going to be -1. So now let me think about how I will do this. I can do a for loop which will give me the index of each of the rows that I want, and for each row, I am going to have a list. Now within that list again, I can do this exact same trick and have column inside of it, but now I put a -1.
        answer_pad = [ [ -1 for j in range(len(text2))] for i in range(len(text1))]

        def recurse(i, j):
            # Base Case: If I am outside of the bounds, then I can stop recursing and give back my promised answer. What is my promised answer? It should be 'for this state, how many subsequence matches are with in these two strings?' and the answer will be 0 because we are invalid!
            if i >= len(text1) or j >= len(text2): # is it actually a problem to do len here? Normally I always force them to be defined as integers, it seems like this would actually increase the time complexity. But Gemini always gives me the answer where len is taken here. So maybe there is something that I am missing that it doesn't negatively impact the time complexity?
                return 0
            
            # Here is where I will check if we have already calculated it yet.
            if answer_pad[i][j] != -1:
                return answer_pad[i][j]

            # They match: In the case that the items match, then I know that I want to move the index on both of them and then ask the question, "All right, for this new state, which is both of them increased, what is your answer?"
            if text1[i] == text2[j]:
                answer_pad[i][j] = 1 + recurse(i+1, j+1)
                return answer_pad[i][j]

            # They don't match: Now in the case that they do not match, I need to make the decision on if I am going to move the first index or the second index. Now I want to actually do both. And so what I'm going to do is I am going to ask that question for both cases. This means that I'm going to move the index of one and keep the other one still and say, "What is your answer?" And then I'm going to do the opposite for the other index and ask what that answer is. And then, because I'm trying to maximize it, I just say that I'm going to take the maximum of both of those.
            else:
                answer_pad[i][j] = max(recurse(i+1, j), recurse(i, j+1))
                return answer_pad[i][j]
        
        return recurse(0,0)


# Trying a similar problem to see if I can do it

class Solution:
    def maxUncrossedLines(self, nums1: List[int], nums2: List[int]) -> int:
        
        def bt(i1, i2, current_answer):
            if i1 >= len(nums1) or i2 >= len(nums2):
                return current_answer
            
            if nums1[i1] == nums2[i2]:
                # We can either choose to perform the cross or not
                return max(bt(i1+1, i2+1, current_answer+1), bt(i1+1, i2, current_answer), bt(i1, i2+1, current_answer))
            return max( bt(i1+1, i2, current_answer), bt(i1, i2+1, current_answer) )
        
        return bt(0, 0, 0)





# This one I watched a video to see the general idea and what I should do, then attempted to build it myself
class Node:
    def __init__(self, key, value):
        self.next = None
        self.prev = None
        self.key = key
        self.value = value

class LRUCache:

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.head = Node(0,0)
        self.tail = Node(0,0)
        self.head.next = self.tail
        self.head.prev = None
        self.tail.prev = self.head
        self.tail.next = None

        self.key_dict = {}
        self.size = 0
        

    def get(self, key: int) -> int:
        # return the value of the key (and also update the structure of the time keeper)
        if key not in self.key_dict:
            return -1
        
        # update Doubly Linked List
        old_node = self.key_dict[key]
        old_node.next.prev = old_node.prev
        old_node.prev.next = old_node.next

        new_node = Node(key, old_node.value)
        old_top = self.head.next
        self.head.next = new_node
        new_node.prev = self.head
        new_node.next = old_top
        old_top.prev = new_node

        # update dictionary
        self.key_dict[key] = new_node
        return new_node.value


    def put(self, key: int, value: int) -> None:
        # Check if it is already in

        # Insert into Doubly Linked List
        if key not in self.key_dict:
            nextNode = self.head.next
            createdNode = Node(key, value)
            self.head.next = createdNode
            createdNode.prev = self.head
            createdNode.next = nextNode
            nextNode.prev = createdNode
            self.key_dict[key] = createdNode
            self.size += 1
            if self.size > self.capacity:
                # Remove the least recently used (which will be the last node in the list)
                remove_node = self.tail.prev
                remove_node.prev.next = remove_node.next
                remove_node.next.prev = remove_node.prev

                del self.key_dict[remove_node.key]
                self.size -= 1
        else:
            # The key is already in my dictionary. This means that I will need to update the value, and it also means that I will need to change the linked list which is keeping track of the oder which keys have been interacted with

            #first I will want to find that node, which I can do because my hash has a pointer to the exact node which I now want to delete
            oldNode = self.key_dict[key]
            oldNode.next.prev = oldNode.prev
            oldNode.prev.next = oldNode.next

            # Insert at top
            created_node = Node(key, value)
            prev_next = self.head.next
            self.head.next = created_node
            created_node.next = prev_next
            prev_next.prev = created_node
            created_node.prev = self.head

            # update dictionary
            self.key_dict[key] = created_node

        


# Your LRUCache object will be instantiated and called as such:
# obj = LRUCache(capacity)
# param_1 = obj.get(key)
# obj.put(key,value)



# This one was not a leetcode problem, but I was asked it in a Microsoft in person live interview. So I want to go back over it.
# Design a rate limiter
# Should have API for request(userId, timestamp) and clearAllOld()

# I will want to be able to check a request by the id to see if they have made more than the limit. I also know that I am going to need a way to efficiently clear out requests from a user which are outside of the the window. My instinct is to have a a dictonary which can keep track of each user by their ID. Then for the value, what can I store which will help me here? I can have the number of requests which they have made. I will also need to have a structure that keeps track of which requests they made and when those timestamps are at. This will make me think of a queue. My first thought is that I want a queue for each of the requestId (so my dict would have a value of a class and in that class it would have both the number of requests and a queue of the timestamps), but the problem that I see with this is that when I want to clear all, I will still need to go through all of the items in my dictonary and check their queue. He was not happy with this and asked me to find a way that I can do it where I only need to itterate through the requests which are out of bounds.
# That once again made me think of a global queue. But I 'feel' that something is wrong with that idea. Let me think about how I would implement it. I would have a global queue of all of the requests that come in, then when I want to clear all, I should be able to only go to those oldest requests and then get rid of them from my dictonary. What is wrong with that? I think I was getting tripped up that multiple requests can come in from the same user, but this should not be a problem because as I go through my que I will just go and decrement the counter by one.

class RateLimiter:
    def __init__(self):
        self.dict = {} #key (userId), value (num of request tracked)
        self.q = deque() # queue of all the requests which I have gotten so far.
    
    def request(userId, timestamp):
        # Check to see if userId has more than allowed.
        # Here I will need to not only check the number which is in my dict for that user, but I will need to have a way to see for that individual user, to see if they have requests which fall outside of the 5 minute time window. I could either itterate through the entire gloabal queue (but that would not be acceptable because the request should be serviced fast), and also does not adhere to the idea of seperation of responsibility. 
        # But here if I change this data structure slightly and have a queue for each individual userId, how does this change things, and what are the implications? I could just itterate though that specific individual queue, and quickly change that. But does this complicate things with the global queue? If I clear out those requests which were found to be old, those same requests will still be in my global queue. When I go to remove them, I will erroniously decrement the user's counter. 
    
    def clearAllOld():
        pass


# I will attempt it with my idea of both a global and an individual user queue
class RateLimiter:
    def __init__(self, maxSize):
        self.dict = {} #key (userId), queue of requests
        self.q = deque() # queue of all the requests which I have gotten so far.
        self.max_size = maxSize
    
    def request(userId, timestamp):
        if userId not in self.dict:
            self.dict[userId] = deque()
            self.dict[userId].append(timestamp)

            self.q.append( (userId, timestamp) )
            return True # we allow the user to send the request

        # First clear out all old requests for this user
        # I want to keep itterating as long as there is a request list for this user (then if I find a request that is still in the window, I know that that is where I need to stop, so I can break)
        while self.dict[userId]:
            reqTimeStamp = self.dict[userId].popleft()
            # within the window
            if reqTimeStamp > timestamp - 5:
                self.dict[userId].appendleft(reqTimeStamp)
                break
            #remove that item from my individual queue (but this is already done because we did a popleft)
        
        if self.dict[userId].size() >= self.max_size:
            return False
        
        # I am free to add one
        self.dict[userId].append(timestamp)
        self.q.append((userId, timestamp))
        return True


        # Check to see if userId has more than allowed.

    
    def clearAllOld(currentTime):
        # Here I should be able to go through each of the items in my global queue
        # How do I deal with those items which I have already removed? Maybe what I can do is to use the global queue as a 'suggestion' which means, this is a possibility for userId's to look at. So it means that I could get false suggestions.
        while self.q:
            reqId, reqTs = self.q.popleft()
            if reqTs > currentTime - 5:
                # This is within the window. so I can stop looking. Put it back in the queue
                self.q.append((reqId, reqTs))
                return
            
            # We need to get this request Id, and attempt to clear it
            while self.dict[reqId]:
                ts = self.dict[reqId].popleft()
                if ts > currentTime-5:
                    self.dict[reqId].append(ts)
                    break


# September 12, 2026

class Solution:
    def orangesRotting(self, grid: List[List[int]]) -> int:
        # Trying to see if I can get all the fresh oranges. I will need to grab all of the rotting oranges. Then because I want to find the number of days, each step from a rotten will be one day. As the newly created rotten orange is created  I can add that to my queue
        rotten = deque()
        fresh = set()
        visited = set()
        for row in range(len(grid)):
            for col in range(len(grid[0])):
                if grid[row][col] == 2:
                    rotten.append((row, col))
                    visited.add((row, col))
                if grid[row][col] == 1:
                    fresh.add((row, col))

        # Traverse the BFS
        days = 0

        while rotten:
            if not fresh:
                return days
            # Keep track of one step for each of the oranges
            num_in_q = len(rotten)
            for _ in range(num_in_q):
                r, c = rotten.popleft()
                for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                    if r+dr>=len(grid) or r+dr<0 or c+dc>=len(grid[0]) or c+dc<0 or grid[r][c] != 1 or (r,c) in visited:
                        continue
                    rotten.append((r,c))
                    visited.add((r,c))
            days += 1
        return -1

# Then changed it to be 
# ...
# if fresh: return -1
# return days
# But this still fails


class Solution:
    def canFinish(self, numCourses: int, prerequisites: List[List[int]]) -> bool:
        # I want to see if I can add all nodes to visited. 
        # I know that this will be a cycle detection in a DAG. I am thinking that I can just start at one node and then do a DFS, and if I encounter a situation where I meet another element on my path, then I know that I have found a cycle. My visited will tell me all of the ones that I have already explored, and so I will need that path variable.
        visited = set()

        # Now I should start randomly at any node. The only thing I am worried about is when I have a node and I find that actually to take that node, the later things depend on it.

        def dfs(node):
            # what should the base case be? What counts as invalid? I guess if it is already in my path?
            if node in path:
                return False
            if node in visited:
                return True
            visited.add(node) # added after realizing
            path.add(node) # added after realizing
            # explore all paths
            # go to that node's adjacency list and see each node
            for nei in al[node]:
                if not dfs(nei):
                    return False
            
            # All nodes passed, return True
            path.remove(node) # added after realizing
            return True
        
        # this has a super strange format for the nodes. I need to think about how I can prepresent the nodes. [0,1] means I must take 1 first, then I am allowed to take 0. I think I can indicate this by representing a connection from 1 to 0 because I am allowed to go from 1 and then go to 0. Do I need to worry about 'fulfilling all prerequisites'? For example, to take class 0, I need class 1, but it is (I remember from math something like nessissary but not suffient), but esentially the idea is that just because one of the conditions is meet, does not mean that all of the conditions are meet, but that particular condition if not meet is enough to invalidate it. 
        # Don't quite know what i am trying to express, or how to capture it in this problem.
        # Maybe I will just create an adjacency list. I have no idea what I am doing (I might need to go watch a Youtube video about these kinds of DAG problems), but I do know that I will need some way to represent the graph. (and why did they give us numCourses?)

        # I want an al that is number of courses long
        al = [[] for _ in range(numCourses)] 
        # This should mean that the index is the node I am talking about, and then all of the nodes in the list at that index are the nodes which it connects to.
        # also maybe that is why they gave us numCourses? because it is required that we know that number so we can create this al fully populated with empty lists?

        for a, b in prerequisites:
            # b needs to be taken first. This means that I need to be on (or have in my visited) b. I think maybe I can represent this as an edge in my adjacency list as the node b is connected (one way) to node a
            al[b].append(a)
        
        # Now what can I do?
        for index, edge_list in enumerate(al):
            # index will tell me the node number that I am on. and then I have that node's edge list
            #dfs()
            # I am thinking about doing a dfs here? Then in my dfs I should check my path. But how can I do this? 
            path = set() # assignment here so it will be a new object, but it is mutable so it will be able to be changable in the helper function.
            if not dfs(index):
                return False


# Then I realized that I didn't track vistited or path, so I added those

# but that fails as well. I asked gemini and it told me that I need to use a three state solution. First off I would have never thought of that. It also shows an interesting way of thinking about states. But I am also thinking that maybe that is what I was actually thinking about when I had this path set and a visited set. So why was my solution failing??

# MY SOLUTION WAS CORRECT!! I just forgot a return True at the end! Gemini just kept randomly hallusinating telling me these random things which were wrong with it! 




class Solution:
    def exist(self, board: List[List[str]], word: str) -> bool:
        # So I need to find a way to traverse the grid such that I am able to determine if letters appear in the same order as word. 
        # not using more than once means I can use visited (or maybe path) as a blocking. In this case visited does not make as much sense because in the previous problems, visited meant that we are doing a singular traversal of the grid. But in this case we are going over 'all possible paths'. This is a backtracking problem. Another thing that I realized about myself is for backtracking I need to investigate this more. I realized that bt is a 'techinque' that I can do ONTO different data structures. It answers the question of 'on this data structure, tell me all of the possible combinations of ___' . I need to think about the different types of data structures that bt can be applied on. I also need to learn how to apply it on them. I also need to think about the different combinations that we might want to generate. (for example difference between permutation and combination)

        # Let try this problem

        def bt(r,c, wordIndex):
            if (r,c) in path:
                return False
            if r>=len(board) or r<0 or c>=len(board[0]) or c<0:
                return False
            if wordIndex == len(word)-1:
                if board[r][c] == word[wordIndex]:
                    return True
                else:
                    return False

            path.add((r,c))

            for dr,dc in [(-1,0),(1,0),(0,1),(0,-1)]:
                if bt(r+dr,c+dc,wordIndex+1):
                    return True
            return False


        for row in range(len(board)):
            for col in range(len(board[0])):
                path = set() # purposfully doing this so that I can see if it is acutally a problem...
                if bt(row, col, 0):
                    return True
        return False

# after I also realized that I didn't block. Once I added the blocking I was able to pass
# I realized that I am only allowed to attempt to traverse if we are currently on a valid letter matching the wordIndex we are trying to find.
# if board[r][c] != word[wordIndex]:
#     return False






class Solution:
    def numDecodings(self, s: str) -> int:
        # this seems like a backtracking problem as well. I don't think it could be greedy because my decision here limits my future options. Plus, we are not asked to find the 'lowest' of something, so it definately is not greedy. We are asked to find the nubmer of ways. So this is definately back tracking.
        # Backtracking enumerates all valid ways, so how can I use bt to perform this? I think I can start at the first letter of the string and see if including this number encoding is valid or not. So now how can I generaize this? For each step, I will be at an index in the string. I will want to answer the question of if I include this current thing (maybe as the grouping passed in), what is my number of ways. If I am not valid to add, then the answer to this question will be 0
        # I think I will use the accumulation method because the bt function should answer the question of from this index, how many ways is possible.
        # but  I have no idea how to keep straight the thing where it seems that my current node position decision. But bt should hold that I only want to consider my state at my exact point. This is a good problem to make sure I learn this point. To do so, I am thinking that I might change the definiation of state to include the current_sum. This way I can see if my previous letter was a 9, now I am at a 3 (both of those are valid individually, but together 93 is not valid). But this still feels like I am not thinking about it correctly. Maybe I could have state include an array of current_choices?


        def bt(index, currentChoices):
            # block the invalid choices?
            if currentChoices and currentChoices[0] == 0:
                return 0
            if currentChoices[0] + int(s[index]) > 26:
                return 0
            
            # what is the valid case? We reach the end
            if index == len(s)-1:
                return 1
            
            # I can do what? what are my options to choose from in the backtracking step? I can either group myself with the previous, or I can group myself with a new group.
            # but I can only add myself if conditions are meet.
            r1 = 0
            if len(currentChoices) == 1:
                r1 = bt(index+1, currentChoices.copy().append(int(s[index])))
            r2 = bt(index+1, [int(s[index])])
            return r1+r2
        return bt(0, [])



class Solution:
    def numDecodings(self, s: str) -> int:
        # Chatgpt told me that I should think about it such that the index which I am at allows me to make a decision that at my current index I am allowed to decide if I want to take only myself, or include the next one. So actually this is kind of like 'looking into the future' where I was previously 'looking into the past'. 
        # Further ellaborating this idea, the index is going to be either +1 or +2 depending on my choice.


        # now that I have this working, can I think of a way to introduce dynamic programming? If my bt(i) is answering the question of 'at this index how many ways can I decode this string'. Then no matter what happened before me, the answer for the same state will always be the same answer. In this case the state is just one variable (index). 
        dp = [-1 for _ in range(len(s))]
        def bt(i):
            # The base cases I also don't understand. I guess these base cases should reflect the traversal path we decide to use below. In some cases, I will decide to go down all possible paths (like the 4 cardinal directions) then I need to block in the base cases, but other times, I only traverse down those valid ones. here I am (assuming I am doing it correctly) validating that we are allowed to be at the index of i. So it is here that I can say, no matter if selected to jump one or jump two indexes, that this is valid. So I think that the case of if i >= len(s): will never be hit, but if that is the case, it should not impact anything because it will just not run.
            # What would be a valid case? I guess when I am at the last letter. So that will be len(s)-1. This is what I have, but it is not right.......
            # Gemini is saying if i == len(s): return 1 but I have no idea why that would be the case. That seems to imply that I am going past my index, but I thought we blocked for that in the way we block for only valid indexes.
            # if i >= len(s):
            #     return 0
            # if i == len(s)-1:
            #     return 1

            #Trying Gemini's solution
            if i == len(s): return 1

            #introducing dp
            if dp[i] != -1:
                return dp[i]

            # now I want to go though my choices and only go down the valid paths that I find. The two base cases assume that the index before me are valid
            # I am realizing that if I am at index where it is 0, this will be invalid for both cases, so I don't need to go down those
            if s[i] == "0":
                return 0
            
            # including only this one
            r1 = bt(i+1)

            # check if it is valid to do the other option
            # Here I am realizing that I am still weak on indexing, slicing, understanding how to target and validate my choices.
            # r2 = 0
            # if i+2<len(s+2) and int(s[i:i+2])<=26:
            #     r2 = bt(i+2)

            r2 = 0
            if i+1<len(s) and int(s[i:i+2])<=26:
                r2 = bt(i+2)

            dp[i] = r1+r2
            return r1+r2
        return bt(0)




class Solution:
    def rob(self, nums: List[int]) -> int:
        # because my current decision limits my future decisions, taking a larger number right now might mean that I miss the opportunity to take a better number in the future. This invalidates greedy. 

        # I am realizing that normally for dp, my state tells me that dimensionality of the dp structure. But here curr_total is infinate, and curr_total is also the thing that I am trying to find, it is the number that should go INTO my dp array. 
        #dp[[-1 for _ in range()]]
        dp = [-1 for _ in range(len(nums))]

        # This should answer the question 'at this index, what is the max number I can get?'
        def bt(i, curr_total):
            #
            if i >= len(nums):
                return 0
            if i == len(nums)-1:
                return curr_total
            
            if dp[i] != -1:
                return dp[i] 

            # I can either choose to rob this house or I can choose to leave this house.

            # Rob this house
            r1 = bt(i+2, curr_total+nums[i])
        
            #Leave this house
            r2 = bt(i+1, curr_total)

            dp[i] = max(r1,r2)
            return max(r1, r2)
        
        return bt(0, 0)



class Solution:
    def rob(self, nums: List[int]) -> int:
        # Gemini says to have the subproblems answer up

        dp = [-1 for _ in range(len(nums))]
        def bt(i):
            if i >= len(nums):
                return 0
            if dp[i]!=-1:
                return dp[i]
            
            r1 = nums[i] + bt(i+2)
            r2 = bt(i+1)
            dp[i] = max(r1, r2)
            return dp[i]
        return bt(0)


# Need to attempt these two.
# 238. Product of Array Except Self
# 3. Longest Substring Without Repeating Characters



# 26 September 2026

# Definition for a binary tree node.
# class TreeNode:
#     def __init__(self, val=0, left=None, right=None):
#         self.val = val
#         self.left = left
#         self.right = right
class Solution:
    def sumNumbers(self, root: TreeNode | None) -> int:

        '''
        # I might be able to use a list for path and have it as a global, or maybe a string
        #path = []
        
        def traverse(node, total, path):
            
            if not node:
                return 0
            
            # append my current node's value
            path = path + str(node.val)
            # if leaf node
            if not node.left and not node.right:
                if not path:
                    return total
                return total + int(path)
            
            leftRes = traverse(node.left, total, path )
            rightRes = traverse(node.right, total, path )

            return leftRes + rightRes
            '''

        def traverse(node, path):
            if not node:
                return 0
            
            # append my current node's value
            path = path + str(node.val)
            # if leaf node
            if not node.left and not node.right:
                if not path:
                    return 0
                return int(path)
            
            leftRes = traverse(node.left, path )
            rightRes = traverse(node.right, path )

            return leftRes + rightRes
            
        return traverse(root, "")


# This is a hacker rank problem
#
# Complete the 'divisibleSumPairs' function below.
#
# The function is expected to return an INTEGER.
# The function accepts following parameters:
#  1. INTEGER n
#  2. INTEGER k
#  3. INTEGER_ARRAY ar
#

def divisibleSumPairs(n, k, ar):
    # Immediately I think this is a two pointers problem.
    # Brute force would be to take those two pointers and then itterate through the loop where I move the j pointer over by one and check to see if it matches the condition (divisible by k). The things that I can think about which might cause a break is if we have less than two elements, then we would just need to return nothing because there are no elements which can be i < j. 
    # This brute force solution would be O(n^2) because for each element in the input array, we will need to itterate all other elements in the array (appearing at an index larger than that element itself).
    
    # One thing that I noticed half way thruogh the problem is that there is ambiguety towards what a 'pair' is. Are we meaning a unique pair? It does not say so, so I think any two combinations of i j which satisfy those two conditions will count.
    
    matches = 0
    for i in range(len(ar)):
        for j in range(i+1, len(ar)):
            #if not (ar[i] + ar[j]) / k: I was attempting this hacky way because I didn't quite know how I can best go about testing for divisibility
            if (ar[i] + ar[j]) % k == 0:
                matches += 1
    return matches