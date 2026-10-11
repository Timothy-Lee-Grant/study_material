
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
