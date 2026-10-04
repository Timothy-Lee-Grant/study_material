
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