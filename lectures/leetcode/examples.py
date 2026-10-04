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


