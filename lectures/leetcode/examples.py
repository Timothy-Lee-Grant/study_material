
# 2 October, 2026:

class Solution:
    def spiralOrder(self, matrix: list[list[int]]) -> list[int]:
        # I want the outter loop to keep going until everything is completely done. So this should check to make sure that all of the conditions are satisfied, then inside of this loop I should keep track to the valid top, bottom, left and right. Then I can go along each of those directions. 
        top = 0
        bottom = len(matrix)-1
        left = 0
        right = len(matrix[0])
        answer = []
        while left <= right or top <= bottom:
            # Now I guess I need to check each of these conditions to see if I am allowed to go down that row or column (then I need to remove that row or column as a valid path).
            # left to right (I can do this along top as long as the rows are not all used up)
            if not top>bottom:
                for i in range(left, right):
                    answer.append(matrix[top][i])
                top += 1
            # Now I want to go down from my right column
            if not left>right:
                # I am now realizing that I might need to think about how when I index, I need to make sure that I did not go out of bounds for answer.append(matrix[i][right]) and answer.append(matrix[top][i]) . So the indexes should be correct because range() has the stop such that it does not include the stop, but when I index those two, I need to actually cut out the invalid index by one
                for i in range(top, bottom):
                    answer.append(matrix[i][right-1])
                right -= 1
            # Go along bottom row. Right to Left
            # We must still have a row
            if bottom>=top:
                # we just decremented right, so I can have it as the start, then I want to go all the way to left, but because range end is not inclusive, then I need to subtract 1 to it (to actually increase it by one).
                for i in range(right, left-1, -1):
                    answer.append(matrix[bottom-1][i])
                bottom += 1
            #now go up along the right most 
            if left<=right:
                # above we already increased top by one, so in the range we will need to have the top as top-1 so that we get the row (but not the row which we have already included when we did the first top left to right)
                for i in range(bottom, top-1):
                    answer.append(matrix[bottom][i])
                bottom += 1
        return answer



# 3 October, 2026:
class Solution:
    def spiralOrder(self, matrix: list[list[int]]) -> list[int]:
        # This is my second attempt after reading the lecture notes, I am tired, but I want to push myself to apply what I read.
        # The ideas that I remember are to think about closed vs half-open indexes, the loop invariant which describes the state which MUST be true at every instance which we hit the start of a loop.

        # I want to have these closed. This means that I want my four bounds to be valid for all within that range, including the number which is contained in the bottom and the right. This means that I will apply the -1 right now.
        # Now what does this mean for the invariant? I know that I will want to have the invariant of the outer loop to say that at the point where we are at the top of the loop, then all four of these coordinates block off the unvisited and remaining valid rows/columns. So I will just need to keep in mind that bottom and right are both valid.
        top = 0
        bottom = len(matrix) - 1
        left = 0
        right = len(matrix[0]) - 1 
        answer = []

        # all four coordinates contain valid rows or columns, and answer contains all the visited nodes in the spiral order.
        # Whith that invariant, what is the conditions which my loop will need to run, and at this point, is my system set up such that the invariant is satisfied to start the first loop?
        while top<=bottom and left<=right:
            # I now want to go along the valid top. This means that I will be be traversing in the same row, but moving through different columns. matrix[(constant row value)][(changing value)] . So I want to think about and articulate what this will look like. There will be a value which will be held constant. This will be the row which I want to go along, then there will be a value which is the index of the column. The row will be given by top. Now I will need to create a for loop which will generate the range which will itterate through the valid columns such that it will go from the first (left most) valid column, to the right most valid column. 
            # I know that because left and right are closed, it means that I need to create a for loop which will start (including) the value of left, and I will need to include the value of right. Because for loop range will not include the stop element (this means that for loop range follows the half-open convention), I will need to add one in this loop to adhear to this. Although this feels like what the lecture notes were warning be regarding doing hand changes to switch domains. But I can not change range's convention, so I will either need to change the convention I am using for left right, top bottom, or I do this.
            for i in range(left, right+1):
                answer.append(matrix[top][i])
            # Now I have gone along this row, it is no longer a valid unvisited row
            top += 1

            # I now want to go down along the right most valid column. So the column will remain constand (and it is targeted with the index at right. Because we chose the closed convention, right will be valid as an index). Then I need to generate a for loop which will produce indexes for which will be valid rows, going from the top down to the bottom.
            for i in range(top,bottom+1):
                answer.append(matrix[i][right])
            right -= 1
        
            # I remember seeing in the answer that we needed to do a guard here. But let me think about why and what it would indicate. We have now changed top and right such that 'the walls are closing in'. I am about to run a loop that must go over a valid row. I am going to be attempting to traverse in reverse order from the right most valid column to the left most valid column, along the bottom most valid row. But it could be the case the when we itterated over top, that we actually went over the last valid row and now we have no valid row. So I should check to see if there are any valid rows left.
            if top<=bottom:
                # Now I can go through and itterate through all of the valid indexes which will be from the rightmost to the left most. Then I will have the index of bottom to be the constant which tells me which row I want to keep constant as I do the traversal over the changing columns.
                # Now here is where I need to think of convention again. right by the closed convention is valid, and left is also valid. But because range uses half-open convention, it will not count left, so when it generates the indexes which should be the valid inices of all the columns I want to itterate over, it will not include the valid index of left. I need to account for this by subtracting one.
                for i in range(right, left-1, -1):
                    answer.append(matrix[bottom][i])
                bottom -= 1
            
            if left<=right:
                for i in range(bottom, top+1):
                    answer.append(matrix[i][left])
                left += 1
        
        # I now need to try to map through on test cases. But this is something that I don't really know how to go through a test case.
        # I pressed submit to see if I got the right answer, so I know that this is wrong, but I should be able to do those walk through of a test case to see what is wrong.
        return answer

# I immediately attempted to follow up the problem after I pressed submit by not looking at the answer and seeing if I could trace through with an example. The trace through took a really long time (like 20 mins, so I have no idea how I would ever do that in an actual interview). Then I still get the wrong answer even though I thought I have it correct now.
class Solution:
    def spiralOrder(self, matrix: list[list[int]]) -> list[int]:
        top = 0
        bottom = len(matrix) - 1
        left = 0
        right = len(matrix[0]) - 1 
        answer = []

        # matrix = [[1,2,3,4],[5,6,7,8],[9,10,11,12]]
        # answer = [1,2,3,4, 8, 12,11,10,9,5,6,7,]
        # left: 1   right: 2    top: 2  bottom: 1
        # itteration range: [1, 2]
        while top<=bottom and left<=right:
            for i in range(left, right+1):
                answer.append(matrix[top][i])
            top += 1

            # At this point we are actually done, but I didn't put a check on it.... But I think it will be the case because we will generate a range which is top:2  bottom:1  so [2,2] this means that it is invalid, but we will still be trying to add this index of row index 2? So we will add to answer, 11? 
            # Let me see if I can put a guard against it. Because I walked though and unless I made a mistake in my walk though, I think I got the right solution so far, I just erroniously enter into this for loop
            if top<=bottom: # This should tell me that I have a row which is still valid, if not it will not attempt to add any more elements to answer
                for i in range(top, bottom+1):
                    answer.append(matrix[i][right])
                right -= 1
        
            if top<=bottom:
                for i in range(right, left-1, -1):
                    answer.append(matrix[bottom][i])
                bottom -= 1
            
            if left<=right:
                for i in range(bottom, top+1):
                    answer.append(matrix[i][left])
                left += 1
        
        return answer

# October 4, 2026
class Solution:
    def spiralOrder(self, matrix: list[list[int]]) -> list[int]:
        # Today is a fresh day. I did this problem yesterday and read the lecture document and tried again, but that time it failed again. Now I will try to do this problem again today to revisit and force into my muscle memory. (I did not read the appendium in the lecture document yet.)

        # the first thing that I remember is that I need to create that over arching loop that will keep going until the problem is solved. I remember (just because of memory) that the lecture docs told me yesterday that I need to use the and condition, and I also remember it said that if we don't have a row or if we don't have a column that it is over, but I am thinking that is it possible that we don't have a row but we do have a column? I don't think so, because that would not make sense. So then why can't I use an or? because wouldn't it be that if one condition is false that the other one will also be false?
        
        left = 0
        right = len(matrix[0])-1 # This will be the closed form of the bound on the columns
        top = 0
        bottom = len(matrix)-1
        answer = []
        while left<=right and top<=bottom:
            # now I want to traverse through each of the index of the columns. So the row will stay constant, and the thing which changes will be the index of the column over the matix. So I need to itterate over the valid index. I chose the closed form of boundaries, so all of those are valid. The range will use the half-open form, so I will need to account for that by putting a +1 or a -1 to ensure that the range gives me that last index element

            # along top, left to right
            for i in range(left, right+1):
                answer.append(matrix[top][i])
            top += 1

            # along right, top to bottom
            if top<=bottom:
                for i in range(top, bottom+1):
                    answer.append(matrix[i][right])
                right -= 1
        
            # along bottom, right to left
            # Is it guaranteed that we have a row at this point? the origional while loop gave the guarantee that left<=right and top<=bottom , so worst case scenario is that top==bottom, then we did the first itteration of `along top, left to right` and now our top (the only remaining valid row has been elemenated). So here I need to do a check to see if I still have a valid row. But what about the other one above. I think I remember from yesteday that I did need to do a check on that one as well. But am I now able to think up the reason right now today?
            # I think the reason might be that I know that the first thing did change the bounds. top was increased, and so my question would be, for the `along right, top to bottom` is there a situation in which the origional while loop contition was valid, but then going along and using up all of the items in a row made me no longer allowed to go and do the `along right, top to bottom`? (this also goes to my origional question when I was doing the while loop of how is it possible that we would have a row but not a column?). I guess in this case because we only changed the bound of top, we have not checked or moved the bound of the columns. This would indicate to me that I should provide a blocking condition on the second one which will make sure that we will have a valid row (because top was just increased.)
            if top<=bottom:
                # I know that I do have a row along which I can itterate through
                # along bottom, right to left
                # so if the left is an index that I want to include in the numbers returned by the range, then I know that now I need to do a change. But let me think about what it would be. I am going from a larger number (right) and going to a smaller number (left). I am decrementing by 1 each time. So it would make sense to me that I would make the stopping conidition even smaller if I wanted to include that number in the half-open converion of the range method. So I will make left smaller by subtracting 1
                for i in range(right, left-1, -1):
                    answer.append(matrix[bottom][i])
                bottom -= 1
            
            if left<=right:
                # along left, bottom to top
                for i in range(bottom, top, -1):
                    answer.append(matrix[i][left])
                left += 1
        return answer


class Solution:
    def climbStairs(self, n: int) -> int:
        # doing this before I read the lecture
        # I know that I have n steps, and I am asked to count how many distinct ways I can climb to the top. I know that this will be a backtracking problem. (then from there I should also be able to simplify it to be dynamic programming because at a particular step, the answer should always be the same for that step). That brings me to the fundamental question that I should always ask myself when I do these recursion problems, what does the recursion function answer: `for this step, this is the number of ways that you can climb to the top`

        dp = [-1 for _ in range(n)]
        def bt(i):
            # base cases, but lets return to the base cases after we do the steps that we can take
            # If I am at the last step, then this is a valid way to which I just took, so I should return 1
            if i == n:
                return 1
            
            # Because we are blocking in the below calls (ie we do not go down and take a two step if we are walking off the edge, there should never be a case where we are having i>n).

            # Now thinking about how to save the answer, if I have previously found the answer for how many ways there are at a given step i, then I should not try to recalculate it.
            if dp[i] != -1:
                return dp[i]

            # from this step we are either allowed to take one step or two steps.
            # should I do my validation here? I know that one of the base cases will be if I reach the last step, so at this point I should have a guarantee that I am not at the last step, so I should be able to take one step, but if I am at the second to last step, then I can not take two steps (that step would not exist).
            one_step_ways = bt(i+1)
            two_step_ways = 0

            # here is another question. What should my blocking condition be? I am starting at step 0 or step 1? So if n is 1, then it means that I need to take 1 step to get to the top, that means that when my number of steps (which in this case is represented by i) is equal to n, then I am at the top. So I can expand this, I can say that if I want to find the number which will block this. I should block when I would otherwise 'walk off the edge' that is when (I am always so bad at these things.....). If n is the last step, my current index is i, and I am at the last step when i==n, then the bad condition will be i<n (but equal is alright). So now in the case here when I am attempting to take two steps, what will this means??? i+2<n this is the case that is invalid. Why did it take me so long to come up with that, and it seems that no matter how many times I do Leetcode, I still cant think of this quickly
            if not i+2<n:
                two_step_ways = bt(i+2)

            dp[i] = one_step_ways + two_step_ways
            
            return one_step_ways + two_step_ways
        
        return bt(0)

# Oct 5, 2026

# I attempted to do Spiral Matrix II today, and I got this as my answer, but I have not submitted the code yet, and I really don't know how I should go about verifying this, and I really want to practice learning how to actually walk through things.
class Solution:
    def generateMatrix(self, n: int) -> list[list[int]]:
        # Fill out a blank nxn matrix
        # I will want n number of indexes. So this means that I want the range function to trigger once is n=1. range starts at 0 and is non-inclusive (half-open). So if I put 1 in range, it will give me back a single element (0), and that is what I am looking for, I want the range to fire once (I don't care which element it gives me).
        matrix = [[-1 for _ in range(n)] for _ in range(n)]


        # Start at index (0,0) and then as we move through the input (in this case the number line), we will place that input in it's associated location.
        row = col = 0

        # I want to keep going until I have reach the end of filling out. But in this case I will not be able to see that I no longer have any rows or columns, here I should stop when my number is passed the final number to be place
        left = top = 0
        right = bottom = n-1 # Here will it be n or n-1? I want to say that my right and bottom should be valid indexs, so I should say n-1
        number = 1 # I am noticing that this 'number' is going to be starting at 1, so this might effect the way I interact with (not the right and botom because those will be checked by row and column), but number will impact the stopping condition

        # Thinking of the smallest case (n=0) and (n=1) if it is 0, I want my while loop to not trigger (the matrix will have had both range function not triggered, so it will be a [[]] and I want to just return that). number starts at 1, so 1<=0*0 will be false. In the case that it is n=1, I want it to fire once. which is what it does (so it is having the equal sign)
        while number <= n*n:
            # Along top, left to right
            for i in range(left, right+1):
                matrix[top][i] = number
                number += 1
            # Just went along the top row, so I need to invalidate that row because it is already filled out.
            top += 1

            # Along right, top to bottom
            # because this is an nxn matrix, and I will hit the stopping (oh no!) I just looked at the example picture and realized that I was wrong. I was about to say that I thought that I might have a guarantee that I will have a place to put the values in this situation. But the example show that I will actually only do the 'top' movement in the second run and will not do the others, so I still need to do the blocking.
            if top<=bottom: # I still have a row left, so I did not just get rid of my final row in the last operation
                for i in range(top, bottom+1):
                    matrix[i][right] = number
                    number += 1
                right -= 1
            
            #I am still having trouble thinking of the guard because is it that I want to see if I still have the thing which I just went through (like the previous operation elemenated a column) so I want to see if I still have an existing column, or is it that I want to see if I still have the thing which I will be attempting to itterate over (in this case I am about to try to itterate over a row)? My guess is that I would want to check the thing which I just shrunk because the thing which I am about to itterate over has not changed yet, but the previous operation might have made it such that the walls closed from the other direction. But in this location, actually there were two previous operations, closing in a row and then closing in a column, so should I guard by checking the rows or the columns? Or do I need both? I remember in the Spiral 1 that I did yesterday, I only did one guard, so I know that it will probably be the same here, but I can't reason through the logic of which one it should be. (I do think that in this case it should be the case that if I am to do this operation, that both should be valid, so to be safe I can just put the guard as both)
            if top<=bottom and left<=right:
                for i in range(right, left-1, -1):
                    matrix[bottom][i] = number
                    number += 1
                bottom -= 1
            
            if top<=bottom and left<=right:
                for i in range(bottom, top-1, -1):
                    matrix[left][i] = number
                    number += 1
                left += 1
        return matrix


# I was able to walk through the problem. I then was able to catch the error which I previously had which was the `matrix[left][i] = number` had the wrong row and columns.
class Solution:
    def generateMatrix(self, n: int) -> list[list[int]]:
        matrix = [[-1 for _ in range(n)] for _ in range(n)]
        row = col = 0
        left = top = 0
        right = bottom = n-1 
        number = 1 

        # input: n = 3 (n*n=9)

        #   1   2   3
        #   8   9   4
        #   7   6   5

        # number = 9
        # left = 1
        # right = 1
        # top = 2
        # bottom = 1
        # loop interval [1, 1]

        while number <= n*n:
            # Along top, left to right
            for i in range(left, right+1):
                matrix[top][i] = number
                number += 1
            top += 1

            # Along right, top to bottom
            if top<=bottom: 
                for i in range(top, bottom+1):
                    matrix[i][right] = number
                    number += 1
                right -= 1
            
            if top<=bottom and left<=right:
                for i in range(right, left-1, -1):
                    matrix[bottom][i] = number
                    number += 1
                bottom -= 1
            
            if top<=bottom and left<=right:
                for i in range(bottom, top-1, -1):
                    matrix[i][left] = number
                    number += 1
                left += 1
        return matrix


# Oct 10, 2026

# Definition for a binary tree node.
# class TreeNode:
#     def __init__(self, val=0, left=None, right=None):
#         self.val = val
#         self.left = left
#         self.right = right
class Solution:
    # Walk through
    # (seems that different types of problems need to have different representation. In this problem, we have a tree, so I need to see how and what the best method of representation will be to perform the walkthrough)
    #
    # root = [3,9,20,null,null,15,7]
    #           3
    #   9           20
    # (.)(.)    15      7
    #
    # Node 3:   return value: 3      left:  1      right: 2
    # Node 9:   return value: 1      left:  0      right: 0
    # Node 20:  return value: 2      left:  1      right: 1
    # Node 15:  return value: 1      left:  0      right: 0
    # Node 7:   return value: 1      left:  0      right: 0
    def maxDepth(self, root: TreeNode | None) -> int:
        
        # This should tell me the maximum depth at node
        def dfs(node):
            if not node:
                return 0
            
            left = dfs(node.left)
            right = dfs(node.right)
            return max(left, right) + 1
        
        return dfs(root)



class Solution:
        # To do the walk through, I think that I will need to go through each 'step' where a step is defined by each of my for loops
        # Or maybe I can just skip to the two for loops which are actually doing 'real work' the others I should be able to just explain in one go what they are doing.
        # sort_array (before): [(10,0),(8,1),(0,2),(5,3),(3,4)]
        # sort_array (after):[(0,2),(3,4),(5,3),(8,1),(10,0)]
        # finish_time:      position:       input_index:
        # (I got too lazy and just submitted it. It passed, so I did it correct, but my way of tracking might not be the best if I am taking so long that I just give up.)
    def carFleet(self, target: int, position: list[int], speed: list[int]) -> int:
        # I know that there is a trick that I should look at the arrival time of each of the cars, I want to see if I can take that info that I was given already, and come up with an answer.
        # I know that I care about the arrival time of each car. I can create an array for this which describes which hour that that particular car arrives where 0 means that it will arrive at the very start, and 1 means that it will arrive in one hour, etc.
        # From that how can I determine fleet? I think that this feels like a monotonic stack type of prolem, but actually it also might just be as simple as walking through the array backwards and seeing if the hour of arrival is larger then the current arrival hour time. I will keep track of that arrival time, and the invariant to this will be that at every point this current_arival will be 
        # current_arrival: the hour at which cars to the left will be limited by. 
        # Finding a car which has a larger arrival time (I realized that it is not strictly even integer hours, but the idea extends seemlessly to floating arrival times), than the current limiting value (current_arrival), I know that this is a new fleet. I will need to update my current_arrival because now this car is the one blocking other which come after it, and I will need to increase the total fleets because this is a new fleet.
        # Initial Conditions:
        # I will start at 0 fleets because at this point I have not found any fleets. This number wil be updated once I found a single car. This initial condition works because if there are 0 cars, there will be 0 fleets (as my loop will not run). If there is a single car, then I will need to make my initial condition such that this car will be definately counted. If I set my current_arrival to be 0, then any car that has a positive arrival time (all of them). If a car has a 0 arrival time, then I guess I would not count it as a fleet. But those would be edge cases which I would bring up to the interviewer.

        current_arrival = 0
        fleets = 0

        # Create an array for each car
        # Bringing in the lecture for array indexing and slices. I want to have car number of elements in this array times. I will use the range method to get the cuts will have 0 as the cut before the first box, and n as the cut after the last box. len(array) gives n which is the last cut. Then range will take all of the elements which are in between those cuts. So it will give the 0th element because cut 0 startes before the box 0, and it will also include the last element because the cut which is n, is after the last element which lives at box n-1 index. 
        # I am wanting to get a for loop that will have n elements. 
        times = [None for _ in range(len(position))]

        # Now go through each of the cars and place their arrival time (assuming no blocking)
        # I am now noticing that position is not in sorted order. I thought that position was going to be in the order which the car were physically at (meaning that the cars would be sorted as either increasing or decreacing). To do this method, I will need to have them sorted. So I need to come up with a way to sort the position array, but keep the associated speed. As of right now, the index of position aligns with the index of the speed. So maybe I can just itterate through the array of position, and then place in as the element a tuple of the position and the speed, then I can sort (because I will put position as the first element in the tuple), then I can finally go through and create this times array.
        sort_array = []
        for i in range(len(position)):
            sort_array.append((position[i], i))
        # In place, assending order. 
        sort_array.sort()

        # Now I am realizing that I sill need the information about the index because I will need to use that information to find who is blocking. So I will change the second parameter from speed[i] to i in my sort_array because if I know i, I will be able to find the associated speed.
        # On second thought I just realized I don't need to do that because THE ENTIRE reason I am doing all of this sorting is the change the positions so I know who is blocking, I don't care about the initial index position. But I will keep it this way with i just because I can still get the speed anyways. But it does show that I am stubling around.
        # Because the sort_array is in assending order, it means that the cars who are closest to the starting line. So the cars in the back are actually going to be the ones who are blocking.
        for i in range(len(sort_array)):
            position, input_index = sort_array[i]
            # finish_time = (total more miles) / time to do one mile
            finish_time = (target - position) / speed[input_index]

            # How do I want to store this into my times array? Do I want to place them from the back or from the start? I will also need to think about how (in which order) I need to go through the list.
            # Cars who are at a larger position will be the ones which are blocking the latter ones. So I will want to itterate through my times array in a way that sees cars who are closest to the finish line first. I can store them in either way.
            # So here I decided smaller positions first (meaning I will need to itterate from the back)
            times[i] = finish_time
        
        # Oh, here we go again with the ranges, and the cuts / boxes. I know from that spiral matrix problem that the correct answer is for i in range(len(times)-1 , -1, -1) but can I think of why that would be the case here using todays lecture of the indexs? There is no -1 cut because the cut represents the start before the element. So how does that make sense here? I know we are going backwards so the rules are different. But anyway, I have spent too much time on this problem, I will just accept this form because I already know it from the spiral matrix.
        for i in range(len(times)-1 , -1, -1):
            # I want to find those cars which would catch up to the other ahead of it, so I will want to see if my current car (at i) is finishing faster then the current limiting time.
            if times[i] < current_arrival:
                # Now I will need to do nothing
                continue
            if times[i] > current_arrival:
                fleets += 1
                current_arrival = times[i]
        
        return fleets


# Oct 11, 2026

class Solution:
    def searchInsert(self, nums: list[int], target: int) -> int:
        # Can I think about which slice this target should to? It is not simply asking me to find the target, but rather to identify the index where it would have been found. So does this break any guarantees? If I find my midpoint to be larger than the target, I might want to move it to say that the target cannot be in that range, and when I do so, I still leave the possibility of having the target at the last slice (so after the final item box). At that point it would have been found to be that the next value after my last element was bigger, but the element immediate to the right was smaller. This satisfies the condition.
        # The smaller case is similar. If I find mid to be smaller than target, I know that I could put the item at the slice 0 and that would be a valid condition
        # This is interesting, I am noticing that I never want to index on right because it is actually outside the bounds of the array. So I think that this is actually why I need to do all of those design decisions which I was feeling as arbitrary when reading the lecture document. The lecture talked about needing to do // on the creation of mid as to round down mid. The reason for this is that we want to ensure that mid will never actually become the number 'right' otherwise it will be out of bounds when we attempt to index it. We also want to look at this in terms of the slice. right is the slice which appears after the last element. The idea was the there are one more slices than there are boxes in these kinds of problems. But we index on boxes.
        l, r = 0, len(nums)

        while l<r:
            mid = (l+r) // 2
            if nums[mid] == target:
                return mid
            if nums[mid] < target: 
                # I remember that from the lecture I need to apply a +1 to the left (but not the right). I know that this will help to prevent an infinate loop, but what does this actually do? Like what does it imply about the actual problem, the state of everything, the contract? I think this will mean that left is always going to be pointing to the next element that it could be (which actually I think is the entire point of this problem, but I still feel unsure about doing this).
                l = mid + 1
            if nums[mid] > target:
                r = mid
        
        # I think at this point if we encountered a situation where l and r have converged, then we are standing at the point where the index should be. 
        return l


class Solution:
    def minEatingSpeed(self, piles: list[int], h: int) -> int:
        # I know that this is binary search because there is going to be some number which lives between 0 and max(piles) which is the speed k which koko needs to eat to satisfy the requirement that koko is able to finish all piles of bananas in the alloted hour h. Although this does assume that h >= len(piles), because koko is limited to only being able to eat one pile per hour, regardless of the eating speed which koko eats at, the maximum number of piles eatten will be equal to (following with a 1-to-1 relationship) the hour which has passed. Koko can only possibly eat at most h piles. But it is possible that koko eats less than h piles. This is the case where koko will not finish one pile within the hour and will then wait for the next hour to finish the pile. This causes hours to increase while piles eaten does not increase. So piles eaten is bound by hours, but hours is not bound by piles eaten. Therefore my previous statement of a 1-to-1 relationship is not true. Maybe I should say that piles eaten is bounded at the top by the linearly increasing function of hours.
        # Anyways, the reason that I know that this is a valid binary search problem is because it will follow the shape of FFFFF...FFFTT....T we will start at an eating speed of 0, and then we have a max eating speed of max(piles). (we are assuming that there will be a valid solution, and we can make that assumption because the constraints say `piles.length <= h <= 109`). So at some eating speed k, we will transition from the false case (of the eating speed does not satisfy the minimum requirement to finish all bananas) to the True state which koko was able to finish all bananas. Now once the true state has been reached, it will remain true until the end. Increasing the eating speed will always still result in koko being able to finish all piles in the alloted time. This problem asks to find the minimum speed which koko needs to eat. So it means that it wants to find the first transition between false to true.
        # Also I can practice thinking about this in terms of the slices and boxes. What is this asking me? I have the boxes which will contain the potential eating speed k. So the box contains a number, and that number is a potential answer. When I am doing binary search, I am trying to find the boundary or the box? The number in the box will result in the state (which in this case is the state of true). Then if I am asked to find the boundary, that will be between the two states of true and false, and because cuts are before the box, the cut which seperates the boundary between the states of False and the states of True, will be before the box of the first element which invokes the state of True. The index of the cut is assocaited with the index of the box it comes before. So in the problem I am asked to find the speed k (the number in the box) which is the first k that produces a state of True, therefore by giving the cut between the boundary, (or giving the indexed box which I found to be equal to target? I'm not so sure about this second one. If I consider the case of repeated values in an array, I can find a target, but it might not be the first one. target=10 nums=[2,3,7.6,7,7,10,10,10,23,23,24,55,87] I could look at my box and find it gives the target (10) but it is not the boundary. Only the boundary gives the first box which transitions from the boxes which contain items that will cause a false state to be a true state).

        # all of this said, lets actually do the problem.
        # I need a list of elements which will be the potential k answers.

        # potential_speeds = [] (on second thought, do I actually need this, or is this one of those problems which is actually using those implicit methods of where a number is of itself indicating the information?)

        l, r = 0, max(piles)

        # so l will be the bound which we know does not contain the answer. All items in the array between speeds[0:l] are all boxes which result in the state of False. Notice this is a slice, l means the index of the cut before the box at index l, so that box at index l might be valid.
        # r will be the cut which I know all all elements from speeds[r:n] will be boxes that result in True. The slice r will means that I already know that the box at index r will result in true. This also has implications on how I select my r at first. r needs to be the cut which is after the last box (because I don't know that the last box is or is not resulting in a state of True). This is also why I never want to attempt to index r.
        # when l==r, this means I have converged on one single location (one single cut). So this means that I know that all values between speeds[0:l] are False, and all values speeds[r:n] are true. So the value which lives at box l (the converged index) must be the first box which contains the first True.
        # but notice what happens if there are no boxes that return the state of True, it will 'at the box' which is past  the last box, so I want to make sure that I don't actually attempt to index it, I just say that this is the cut, or say that because I find the cut, the box which would contain the first true is at the index associated with the cut.
        while l<r:
            mid = (l+r) // 2
            condition = find_true_false_condition(mid)
            if condition:
                # The box which lives at mid makes the state True
                l = mid+1
            else:
                r = mid
        return l


# October 18, 2026

class Solution:
    def hasPathSum(self, root: TreeNode | None, targetSum: int) -> bool:
        
        # I can not calculate the sum at the invalid (when Ireach an invalid because that will not tell me if the parent is a leaf.) I will only be able to check if the node I am currently on is a leaf node if both of my childern are empty
        def traverse(node, passed_in):
            if not node:
                return False
            
            current_sum = passed_in + node.val

            if not node.left and not node.right:
                if current_sum == targetSum:
                    return True
                return False
            
            return traverse(node.left, current_sum) or traverse(node.right, current_sum)
        
        return traverse(root, 0)



class Solution:
    def findRepeatedDnaSequences(self, s: str) -> list[str]:
        # The first idea that I had was to have a set which each time I moved my window over by one, I would add a count of how many of each letters I had. then as I keep sliding my window, I will need to check to see if there is already a combination of that type. But I am also seeing that I will need to keep track of the order that these appear in as well. So that method will not work.
        # The Brute Force approach would be to: Let me think about this, I actually don't quite know what the brute force approach would be here. I want to find an indefinate (oh wait, no it is definate. it is 10 units long). So maybe I could look at a 10 element window, then for each ten element window, I would look one unit to the right and see if that is a repeated of my 'current window'. Then I would need to do that for all windows to the right for my 'current window'. Only then could I slide my current window over by one.
        # I need to think about what even makes this problem hard.

        # I will attempt to build a window
        window = []
        i = 0
        while i < len(s):
            if len(window) == 10:
                break
            window.append(s[i])
            i+=1
        
        # I want to be able to slide this window, so now I am thinking that I need a queue (so in python a deque)
        # And I will need to actually have two kinds of loops. The first loop will be for moving once each time I want to slide my 'current window' and the inner loop will be for that current window, I will want to build (or maybe slide my window over again?)

        # I have no idea


# This is my first attempt after looking at the 'idea' from ChatGPT. I didn't look at the code yet. I also have not ran the code. I will put this here with all of my comments, then I will delete the comments and attempt to do a walk through and see if I can catch my errors.
class Solution:
    def findRepeatedDnaSequences(self, s: str) -> list[str]:
        # I looked at ChatGPT and will now re-attempt to do this problem.
        # It told me the idea of using a seen and slicing the string s
        # Although I did not look at the code which ChatGPT generated, because I will first try it here.

        seen = set()
        already_added = set()
        result = []

        # I will want to stop when I no longer have a valid window in s to look into. I want 10 elements to the right of my current index
        i = 0
        # while i < len(s):     This would be the normal way to block for index of i. But I want to ask for the window of i, and I want to take 10 elements. s[i:i+10] will be my range, so I need to stop when? Thinking about this in term of cuts and boxes, i will be the index of the element I want to place into my window. It will be a box. But in the context of this range, i is actually the starting cut which encloses the 10 elements that I want to capture, and so that means that the last element which I want to validly capture will be at (i+10)-1 index (I mean that will be the box which I will try to index). This will need to be valid and once i get to be one more and that is outside of the length of s, that is when I want to stop

        # This is my first 'gut feeling' after writing that logic above, but I will need to do so tracing and think about it more before I submit.
        while i+10 < len(s):
            # Grab the window
            window = s[i:i+10]

            # if window in seen:
            #     # I am realizing if I do it this way, then I will append each time that I see a repeat, but I should only append one single time. So to fix this I will add another see to show already added elements to my result.
            #     result.append(window)

            if window in seen and window not in already_added:
                already_added.add(window)
                result.append(window)
            
            # sets can add elements again so I can add window here regardless of if it is already in seen or not
            seen.add(window)
            i+=1
        
        return result


# (submitted it and it was correct)
class Solution:
    def findRepeatedDnaSequences(self, s: str) -> list[str]:

        seen = set()
        already_added = set()
        result = []
        i = 0

        # s = "AAAAACCCCCAAAAACCCCCCAAAAAGGGTTT"
        # window = ""
        # seen = ()
        # already_added = ()
        # result = []


        # I am thinking that the way I have it above is not a good way to represent it because the lecture documents talk about being able to go and add a new row each itteration. So I will try to represent it in that way.

        # s = "AAAAACCCCCAAAAACCCCCCAAAAAGGGTTT"
        #   i   window          seen                        already_seen            result
        #   0   "AAAAACCCCC"    ("AAAAACCCCC")
        #   1   "AAAACCCCCA"    ("AAAAACCCCC","AAAACCCCCA")

        # Here we go, I am seeing that this is going to take a long long time before I would be able to go through each of these letters for the entire string. This would take up way too much time in an interview. I would also get lost in terms of each time I need to refind the 'ending' of the last letter that I was looking at. This is making me think that maybe I should use ( ... ) to represent the window. I am also seeing that seen and already_seen are going to explode in terms of length and it will be impossible to show them cleanly.

        # s = "AAAAACCCCCAAAAACCCCCCAAAAAGGGTTT"
        #   i   window                                      result
        #   0   "(AAAAACCCCC)AAAAACCCCCCAAAAAGGGTTT"
        #   1   "A(AAAACCCCCA)AAAACCCCCCAAAAAGGGTTT"
        # ...
        #   11  "AAAAACCCCC(AAAAACCCCCC)AAAAAGGGTTT"        ["AAAAACCCCCC"]

        # But at this point I am just 'looking at it' and jumping to the index I see has a repeat. This isn't really what I should actually be doing.

        # I guess for now I have documented my struggle and thought process with the walkthrough portion. I will now attempt to see about the window length and what my bounds should be for while i+10 < len(s): (to see if this was actually correct or not).
        # s[i:i+10] is the range, it means that I will want to be able to have my last cut at i+10. It does not mean that I want to index this i+10 element. I only want to index the (i+10)-1 element (box). len(s) will tell me how many elements which are in s. I will want to think about how len(x) corresponds to the final index. Normally I want to stop when i == len(s) (this means I DON'T want to run that loop, which is why I do while i<len(s). ) So now applying this here. It should just be the same thing but I can 'group' this i as the exact same type of thing. I can conceptulaize it as 'the element which I want to be able to grab and index'. So I will ask myself which is the element which I am wanting to grab and index? It will be i+10-1.
        # So let me apply the same rules here. while i<len(s): => while (i+10-1)<len(s)
        # But once again, this just does not feel right. Because I know that I am doing the < and not <=
        # but I have spent too much time on this problem. I will submit it anyways and see what is happening.


        while i+9 < len(s):
            window = s[i:i+10]

            if window in seen and window not in already_added:
                already_added.add(window)
                result.append(window)
            
            seen.add(window)
            i+=1
        
        return result

class Solution:
    def findMaxAverage(self, nums: list[int], k: int) -> float:
        # Standard fixed size window, objective is to maximize total sum within window, where window is of length k.

        total = 0
        current_max = 0
        i=0
        # Once i is equal to len(nums) this will be out of bounds.
        while i < len(nums):
            # We are still in the process of building our window
            # I want to think about this bound a little bit. i is my current index (the element that I am including). i will be the frounteer, meaning that my window will be backwards looking. I also know that I want k elements in this window. But because i in this context is the element (box) which I am attempting to add (not the slice/cut which appears before the box element), I will actually say that i is inclusive because I am including this i element. So the cut of the range would actually be at i+1 (because that is the cut which encloses the final element, which will be element i). So now the range I am looking at is range(x:i+1) and I want this to have k elements. (I need to find the x).
            # This means that I want to take k steps, from the i+1 cut. (i+1)-steps => (i+1)-k
            # That will represent the cut which is at the front of the first element which I want to enclose for my window. 
            # But how does that translate into this 'if i < k:' expression which I am attempting to build to check if my window is fully built? 
            # I might be able to think about it in simplified terms. if my k is 2 it means that I want two elements. Then if I am at index 0, it means that during this loop I will be including index 0. So my cut will be 0+1=>1. Now my window has not yet been built. So I need to increase my window size. I will then have my index go to be 1, which will result in the cut of 2 (because that is the cut which encloses the inclusive element of 1). That means that this particular loop will be the loop which my window will be fully built (I am just noticinging right now that actually I don't want to go to my else statement in this type because I don't want my last element to drop off...). So that means that I still want to run this 'building my window' section when I am at this step. That means that this itteration I am still building my window, and I can think of it at 'placing the final block'.
            # Now when i goes to the next one i will be 2 (so i==k) This is the time which I don't want to run the 'building the window' block. So my initial guess of 'if i < k:' was correct. But this took way too long to reason through and I feel this shows that I still have some things that I need to work on here! 
            if i < k:
                total += nums[i]

                # I am also noticing here that once I build my first 'valid window' I will want to put it in as my current max because it is a valid window.
                if i == k-1:
                    # Also realized that it said to have it as the average
                    current_max = total / k
            
            # This means that we already had our full window built
            else:
                # kick out element that dropped off
                # Which index should I kick off? I want to add element i so it means that I want to kick off the element which will be k steps from i? If i is 0, then it means I want 0 elements, so I would kick off i itself (with no steps) Good. Then if k is 1, I will move over one element and kick that off. Good
                total -= nums[i-k]

                # add element at index i
                total += nums[i]

                # check to see if we have a new max
                current_max = max(current_max, total/k)
            
            i += 1
        
        return current_max


# I think this one will be a good problem to go over in the future for 'walking through'. Right now I was trying to go through a bunch of problems today, and so I did not do a full walk through. But I looked at my error and now I see that my k is counting the number of duplicates instead of the number of valid elements. But I should do a walk through of this code in the future and see that I can catch this error.
class Solution:
    def removeDuplicates(self, nums: list[int]) -> int:
        # because I know that this is a sliding window problem my brain will look there. But from immediate reading of the problem, I don't think I would have guessed that this is a sliding window problem.
        # I have a sorted array (increasing), I want to remove the duplicates. I do not want to create a new data structure, all operations should be done to the origional nums array.
        # The problem talks about k, but this is not a passed in parameter. This is the answer that we need to find. We need to find how many unique elements that are within the sorted array. 
        # My first idea is that I might be able to keep going through my array and I also know that as I go through my array, all of the duplicates will be the immediate neighbors of my element, because the array is sorted.
        # So now I will need a way to move over those elements? (or do I just need to return k and I can leave the actual array alone?). Looks like we do need to change the array itself, but the examples show that I can place anything in the back (after this k elements). 
        # So how will I want to do this operation? I will have my pointer i, and I will be able to keep going until I reach a new value. OH! This is that reader writer method!!! This is different than the fixed window I was initially thinking because of the previous problems which I was doing. 

        # Let me recall this reader/writer strategy
        # reader: goes ahead. Looks for first valid element
        # writer: Is at index which will be written to. 'Place next valid element here'

        # I like having names to associate with strategies!!!! 

        reader = 0
        writer = 0
        k = 0 
        while reader < len(nums):
            # I think I might need a special case for the first time, because I want to check the previous value
            if reader != 0 and nums[reader] == nums[reader-1]:
                # In this case, go to the next element because reader is currently pointing to an invalid element. keep writer where it is.
                reader += 1
                k += 1
                continue
            
            elif reader == 0:
                # this will be guaranteed to be unique because there have not been any elements in the array
                # maybe I could have just changed my initial conditions for reader and writer
                reader += 1
                writer += 1

                # yeah, I should have just had reader and writer as starting at 1. but this shouls work as well.
                continue
            
            else:
                # This is the case where reader is pointing to a valid index, and my writer needs to write this value into it.
                nums[writer] = nums[reader]
                reader += 1
                writer += 1
                
        return k


class Solution:
    def search(self, nums: list[int], target: int) -> int:
        # I remember hating this problem a long time ago.
        # I see that this is a search problem. I also know that for binary search it has that mononic (so something) property where it is FFFF...FTTTT...T shape. But now that this is rotated, the shape is no longer there. 
        # Is it that I will need to adjust my definition of what True and False is?

        # Let me just see if I can start writing something before I really think of a full solution....
        l = 0
        # r will be out of the bound, but that is OK because these binary search problems have l and r, encompasing the range of possible valid ranges (so it is a range, not the box index).
        r = len(nums)   
        while l<r:
            # I guess I still find a mid index,
            mid = (l+r)//2

            # because all elements are distinct, I know that if I am at the target value, this is the index I am looking for.
            if nums[mid] == target:
                return mid
            
            # Now for the hard part. I need to try to adjust my bounds. (Notice that right now I am 'making it up as I go', this would be really bad for an interview).
            # I know that left element is no longer guaranteed to be the smallest element. I also know that at some point there will be a pivot. I know that from left to pivot, all points will increase. I also know from pivot to right, all elements will increase. The pivot could be on either ends as well.
            # But I don't know pivot.
            # Ok, I think I see. I have my mid point and this is the thing which I want to cut my range in half with. I know that the element (if it exists) is in range(l:r). 
            # So this means that my goal will be to determine which side of mid that I want to cut off.
            # I should check if my mid is larger than my right. If that is the case, then I think it should be that I will be able to say that my target is in the left half range(l:mid) (and because we already checked that mid is not the answer, we want to exclude it from the range, and because in here mid will be a cut, this does exclude the element at index mid).
            if mid > nums[r-1]:
                r = mid
                continue
            
            # Now what if 'mid < nums[r-1]' is this guaranteed to be that we are looking in the other half?
            # I don't know. I am too tired right now to think. I will come back to this problem later. As of now, I have not looked at the solution, I have not ran the code, and when I come back I will attempt to solve it, and then see if I can do a walk through before I run my code, or look at hints / answers.



# Oct 20, 2026

# First attempt done without thinking much
class Solution:
    def maxArea(self, height: list[int]) -> int:
        # I have already done this problem before so I know that I need to use that trick of my two pointers seperated and move inward.
        # I am noticing that water is actually allowed to 'go through' walls in this problem. So walls which are part of the items in the place in between the two walls that I am looking at are almost like they are not there.

        l = 0
        r = len(height)-1
        result = 0
        while l<r:
            volume = min(height[l], height[r]) * (r-l)
            result = max(result, volume)
            if height[l] > height[r]:
                r-=1
            else:
                l+=1
        return result

        # I want r to be initialized to len(height)-1 because it is not a cut. In the binary search problems, right was set to len(array) because actually that last cut was indicating that the number was not in the array. But here, each of these will be indexes. 
        # I also am thinking of the question about distance and the stopping condition. When I am at the same wall, it does not make sense to calculate the volume because the volume of a single wall encapsulates nothing.
        # When calculating distince, I think it makes sense that the distance will be 'how many steps from one element to the other'. This can be seen if I look at two walls right next to each other, they will have a width of one.
        # The reason that I was selecting to move the pointer to the wall of the lower wall was that I started at the farthest away and I have already logged that as a potiential solution. Now, I need to move one of the pointers. By keeping the higher of the two walls, the limiting factor is the lower wall, by keeping the lower wall, 

        # Walk Through
        # height = [1,[8,6,2,5,4,8,3],7]
        #   l       r       volume      result
        #   0       8       8           8
        #   1       8       49          49
        #   1       7       18          49
        #   ...

        # height = [1,1]
        #   l       r       volume      result
        #   0       1       1           1
        #   1       1       -           -       (loop doesnt run)
        # returns: 1

        # I then submitted this code and it passed.


class Solution:
    def maxVowels(self, s: str, k: int) -> int:
        # I see that we are given a fixed window size of k, so I know this will be a sliding window problem using a fixed size of k. 
        # It is asking me to find the maximum window of this fixed size for the number of vowels. I don't think I will need some kind of set for this problem, instead I can just have a counter which will check if the item that we are currently adding or dropping from the window is or is not a vowel.

        i = 0
        res = 0
        vowels = 0
        while i < len(s):
            # Building window section
            if i < k:
                if s[i] in ['a', 'e', 'i', 'o', 'u']:
                    vowels += 1
                res = max(res, vowels)
            
            else:
                # add new element
                if s[i] in ['a', 'e', 'i', 'o', 'u']:
                    vowels += 1

                # kick out 'out of window'
                if s[i-k] in ['a', 'e', 'i', 'o', 'u']:
                    vowels -= 1
                
                res = max(res, vowels)
        return res

        # Walk through
        # s="heello_" k=2
        #   i       vowels      res
        #   0       0           0
        #   1       1           1
        #   2       2           2
        #   3       1           2
        #   4       0           2
        #   5       1           2
        #   6       -           -       (loop doesn't run)
        # returns: 2

        # I then submitted the code and it passed.

class Solution:
    def dailyTemperatures(self, temperatures: list[int]) -> list[int]:
        # I know from past, that this was the monotonic increasing or decreasing stack. I have not read the lecture document on stacks yet. I will see if I can figure out how this idea will be able to help me in this situation.

        # I am looking to find the next warmer day (so the next day with a larger temp). Therefore if I encounter a day, I will need to put it in my stack and wait until I find a next element which is 'resolving it' meaning an element that is larger. 

        # I see how I can 'find the next larger element', but this wants to know how many days appart those elements are. I guess I could actually store a tuple where each time I put an element into the stack, I will also add the index which that element appeared. This will also help me to build the answer array

        answer = [0 for _ in range(len(temperatures))]
        mystack = []
        i=0
        while i < len(temperatures):
            # Here I will need to have my element (which is the temperature of the particular day that I am looking at right now.). This will be temperatures[i]
            # I can not assume that I do have elements in my stack, or that I don't. But for each day, I know that I will want to go back and ask the question, did this day resolve any of the elements in the stack (which the stack represents all of the elements which are currently waiting to be resolved. They want to find a day in the future which will be larger. Here I am, a day in the future, and I am going to see if I am larger. If I am larger, then I have satisfied the condition and I can resolve that past element.).
            # Thinking about the shape, I will keep removing the smaller elements, then I will place my current element into the stack at the top. This means that I have removed all of the smaller elements from my stack, which are smaller than my current element, and now I place my current element as the smallest element in the stack at the top. This means that my stack will have the absolute largest element seen so far at the very bottom of the stack. So the stack shape will be largest to smallest (where largest is at the deepest parts of the stack). This means that the elements are decreasing in the stack. As I pop, I will continually get larger and larger values. So this is a monotomically decreasing stack.

            # Resolve previous days
            while mystack and mystack[-1][0] < temperatures[i]:
                # the element at the top of the stack is smaller than my current day. I will need to fill out my answer array for this day.
                prev_temp, prev_index = mystack.pop()
                # answer array will need to place the index of the next higher temperature in it. This means that it is the index of our current day.
                #answer[prev_index] = i
                # During the walk through I noticed that actually the problem wanted me to find the days I need to wait, not the index of the next hotter day
                answer[prev_index] = i - prev_index

                # We want to keep doing this until my entire stack is out of elements (mystack returns false), after which we have found the highest temperature day which has been seen so far and we have resolved all elements that we have seen so far. Under this case, we need to place our current day in the empty stack (which I have the outline for below). If our stack is not empty, but we encounter a day which is either larger (or equal to), because the problem question says that we need to find the next higher day, an equal day is not a valid resolution. So we need to stop popping elements from the stack and we need to place the current day in the stack (also the same thing which I have scaffolded out below).


            # Add current day into stack.
            mystack.append((temperatures[i], i))

            i+=1
        
        # because I filled out the answer array with all 0s, I can just return answer array here. The elements remaining in our stack were unresolved. This means that we placed them into our stack because we were waiting until we found a larger element, the remaining elements in our stack represent the days which we have not found any larger elements in their future. So those elements need to have their index in the answer array be 0, but because the only time that I touch the answer array is when I am resolving a day, if that day was not resolved, then it will still be 0.

        return answer

        # Walk through
        # temperatures = [73,74,74,75,71,69,72,76,73]
        #   i       prev_tuple       mystack             answer
        #   0       -                [(73,0)]            [0,0,0,0,0,0,0,0,0]
        #   1       (73,0)           [(74,1)]            [1,0,0,0,0,0,0,0,0]
        #   2       -           [(74,1),(74,2)]            [1,0,0,0,0,0,0,0,0]
        #   3       (74,1)           [(75,3)]            [1,2,1,0,0,0,0,0,0]
        #   4       -           [(75,3), (71,4)]            [1,2,1,0,0,0,0,0,0]
        #   5       -           [(75,3), (71,4), (69,5)]            [1,2,1,0,0,0,0,0,0]
        #   6       -           [(72,6)]            [1,2,1,3,2,1,0,0,0]
        #   7       -           [(76,7)]            [1,2,1,3,2,1,1,0,0]
        #   8       -           [(76,7), (73,8)]            [1,2,1,3,2,1,1,0,0]

        # I then submitted my code and it passed.