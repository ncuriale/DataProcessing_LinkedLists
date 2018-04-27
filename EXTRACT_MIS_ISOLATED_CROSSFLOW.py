#Module imports
import re
import os
import sys
import numpy as np
import time

class Node:

	def __init__(self,x,Mis):
		self.x=x
		self.Mis=Mis
		self.next=None
		self.prev=None

	def getMis(self):
		return self.Mis

	def getX(self):
		return self.x

	def getNext(self):
		return self.next

	def getPrev(self):
		return self.prev

	def setMis(self,Mis):
		self.Mis=Mis

	def setX(self,x):
		self.x=x

	def setNext(self,next):
		self.next=next

	def setPrev(self,prev):
		self.prev=prev

def tecplot_reader(file, nvar):
	"""Tecplot reader."""
	nodeData = []
	elementData = []
	skip=0
	init=0
	head=1
	dataInit=0
	with open(file, 'r') as fid:
		for idx, line in enumerate(fid.readlines()):
			'''
			if idx>30:
				return data
			'''
			#Check if start of new zone
			A = re.search(r'ZONE (.*$)', line, re.M | re.I)
			if A:
				init=idx
				skip=1
				head=0

			#Skip lines after start of new zone before data points
			if ( skip==1 and (idx-init)<5 ) or ( head==1 ):
				#Check for zone info
				B = re.search('Nodes=*', line)
				if B:
					info=line.split(',')
					nodes=float(info[0].split('=')[1])
					elements=float(info[1].split('=')[1])
				#Index for start row of data in file
				dataInit=idx+1
				continue
			#Otherwise add data to array
			else:
				#Set row index
				rowIndx=idx-dataInit

				#First collect nodes
				if ( rowIndx<nodes ):
					lineData = [float(i) for i in line.split()]
					nodeData.append(lineData)

				#Second collect elements
				if ( rowIndx>=nodes and rowIndx<nodes+elements ):
					lineData = [int(i) for i in line.split()]
					elementData.append(lineData)

				skip=0

	return nodeData,elementData

def defineLinkedList(nodeData,elementData):

	#Modify element data indexes to be base_0
	elementData=alterDataIndexes(elementData)
	linkedList=setLinkedList(nodeData,elementData)
	linkedList,listIndexes=checkForMultipleLists(linkedList)
	
	return linkedList,listIndexes

def alterDataIndexes(elementData):

	for i in range(len(elementData)):
		for j in range(len(elementData[0])):
			elementData[i][j]=elementData[i][j]-1

	return elementData

def setLinkedList(nodeData,elementData):

	linkedList=[]
	#For all node data, make a node object, then save in linked list array
	for i in range(len(nodeData)):
		temp = Node(nodeData[i][0],nodeData[i][1])

		#Compare for connectivity data to nodeData indexes
		for j in range(len(elementData)):
			if i==elementData[j][0]:
				temp.setNext(elementData[j][1])
			if i==elementData[j][1]:
				temp.setPrev(elementData[j][0])

		#Add to linked list array
		linkedList.append(temp) 

		#print temp.getX(),temp.getMis(),temp.getNext()

	return linkedList

def findHeadAndTail(linkedList,init):

	inext=init
	for i in range(len(linkedList)):
		inext=linkedList[inext].getNext()
		if inext is None:
			break
		tail=inext

	iprev=init
	for i in range(len(linkedList)):
		iprev=linkedList[iprev].getPrev()
		if iprev is None:
			break
		head=iprev

	return head,tail

def getHeadAndTail(linkedList,indx=0):

	#Find head and tail indexes
	head,tail=findHeadAndTail(linkedList,indx)

	#Get head and tail values
	headVals=[linkedList[head].getX(),linkedList[head].getMis()]
	tailVals=[linkedList[tail].getX(),linkedList[tail].getMis()]

	return head,tail,headVals,tailVals

def checkForMultipleLists(linkedList):

	#Get initial head and tail
	head,tail,headVals,tailVals=getHeadAndTail(linkedList)
	lists=[head,tail]

	#Check lists for common X-distance and link chains based on this
	for i in range(len(linkedList)):
		if i==head or i==tail:
			continue
		vals=[linkedList[i].getX(),linkedList[i].getMis()]
		if vals==headVals or vals==tailVals:
			#If values the same as original head and the current list is also a head
			if vals==headVals and linkedList[i].getPrev()==None:
				#flip indexes 
				linkedList=flipLinks(linkedList,i)
				#link but skip current index (remove from chain)
				linkedList[head].setPrev(linkedList[i].getPrev())
				linkedList[linkedList[i].getPrev()].setNext(head)
				#change head
				head,tail,headVals,tailVals=getHeadAndTail(linkedList,i+1)
				lists=[head,tail]
			#If values the same as original tail and the current list is also a tail
			elif vals==tailVals and linkedList[i].getNext()==None:
				#flip indexes
				linkedList=flipLinks(linkedList,i)
				#link but skip current index (remove from chain)
				linkedList[tail].setNext(linkedList[i].getNext())
				linkedList[linkedList[i].getNext()].setPrev(tail)
				#change tail
				head,tail,headVals,tailVals=getHeadAndTail(linkedList,i+1)
				lists=[head,tail]

			#lists.append(findHeadAndTail(linkedList,i+1))

	return linkedList,lists

def flipLinks(linkedList,initIndx):

	#Go through all indexes of current chain and flip
	inext=initIndx
	for i in range(len(linkedList)):

		#Get indexes
		currInd=inext
		inext=linkedList[currInd].getNext()

		#Flip indexes
		linkedList[currInd].setNext(linkedList[currInd].getPrev())
		linkedList[currInd].setPrev(inext)

		if inext is None:
				break

	return linkedList

def searchLinkedList(linkedList,listIndexes,val):

	#Search list for matching value -- break if found or end of sublist (None index)
	inext=listIndexes[0]
	for i in range(len(linkedList)):
		inext=linkedList[inext].getNext()
		if inext is None:
			break
		if linkedList[inext].getMis()==val:
			matchIndex=inext
			return matchIndex

	return None

def findPlateauMach(linkedList,initIndx):

	def getSlope(data,ind1,ind2):
		dy=data[ind2].getMis()-data[ind1].getMis()
		dx=data[ind2].getX()-data[ind1].getX()
		return float(dy/dx)

	def testDirection():
		currX=linkedList[initIndx].getX()
		nextX=linkedList[linkedList[initIndx].getNext()].getX()
		prevX=linkedList[linkedList[initIndx].getPrev()].getX()

		nextDX=nextX-currX
		prevDX=prevX-currX

		if nextDX>prevDX:
			dir=1
		else:
			dir=0

		return dir

	def loopNext(indx,dir):
		if dir==1:
			val=linkedList[indx].getNext()
		elif dir==0:
			val=linkedList[indx].getPrev()
		return val

	#Get direction of increasing X values
	dir=testDirection()

	#Find max negative slope in search range and calculate the critical slope
	indx=initIndx
	maxSlope=1e30
	for i in range(searchRange):		
		#Get slope for this index
		slope=getSlope(linkedList,indx,loopNext(indx,dir))
		#Check
		if slope<maxSlope:
			maxSlope=slope
			criticalSlope=maxSlope/10
		#Next index
		indx=loopNext(indx,dir)

	#print maxSlope,criticalSlope

	#Set some variables
	cnt=0
	indx=initIndx
	left=initIndx
	right=initIndx
	#Look through search range
	for i in range(searchRange):
		
		#Get slope for this index
		slope=getSlope(linkedList,indx,loopNext(indx,dir))

		#################
		#    Checks     #
		#################
		#Look for slope at left to change first
		if left==initIndx:

			if slope<criticalSlope:
				cnt+=1
			elif slope>criticalSlope and cnt>slopeSensor:
				cnt=0
				left=indx #Set value once sensor is met
				right=loopNext(indx,dir)

			'''
			if slope<0:
				cnt+=1
			elif slope>0 and cnt>slopeSensor:
				cnt=0
				left=indx #Set value once sensor is met
				right=loopNext(indx,dir)
			'''
		#Look for slope at right to change after
		elif left!=initIndx:

			if slope<criticalSlope:
				cnt+=1
			elif slope>criticalSlope:
				cnt=0
				right=loopNext(indx,dir)
			#Once slope has been different for sensor length, hten break
			if cnt>slopeSensor:
				break

			'''
			if slope<0:
				cnt+=1
			elif slope>0:
				cnt=0
				right=indx
			#Once slope has been different for sensor length, hten break
			if cnt>slopeSensor:
				break
			'''

		#print i,indx,slope,left,right,cnt,linkedList[left].getMis(),linkedList[right].getMis()
		#Next index
		indx=loopNext(indx,dir)

	#calculate average of left and right to return as plateau value
	ave=( linkedList[left].getMis()+linkedList[right].getMis() )/2
	
	return ave

def main():

	#Ensure files are named correctly and present
	fileName = str(sys.argv[1])
	#os.system("mv "+fileName+" NA1088_VAFN14_case4.plt")

	#searchRange --> Critical amount indexes to search for changes in slope
	#                Will not search further then this value from the max Mis
	#slopeSensor --> Amount of indexes to satisfy changes in slope
	global searchRange
	global slopeSensor
	searchRange = int(sys.argv[2])
	slopeSensor = int(sys.argv[3])
		
	#if not os.path.exists("NA1088_VAFN14_case4.plt"):
	#	print "Tecplot data file does not exist -- please name carefully"
	#	return
	#elif not os.path.exists("extractMis.mcr"):
	#	print "Extract Mis macro file does not exist -- please name carefully"
	#	return
	
	#Read tecplot macro file
	#with open ("extractMis.mcr", "r") as fid:
	#	scriptLines=fid.readlines()
	#fid.close()
	
	'''
	#Get correct Path
	cwd=os.getcwd().replace('/', '\\')
	split=cwd.split("aero")
	path_head="Z:"
	PATH=path_head+split[1]

	#Set path variable to change
	HEAD="$!VarSet |MFBD| = '"
	TAIL="'\n"
	scriptLines[2]=HEAD+PATH+TAIL
	'''
	'''
	#Change Mach variable
	MACH = raw_input("What is the Mach Number of this simulation? ")
	type(MACH)
	HEAD="  EQUATION = '{Minf} = "
	TAIL="'\n"
	scriptLines[14]=HEAD+MACH+TAIL
	
	#Alter macro file
	os.system("rm -f temp.mcr")
	os.system("touch temp.mcr")
	fid=open("temp.mcr", "w") 
	for i in range(len(scriptLines)):
		fid.write(scriptLines[i])
	os.system("mv temp.mcr extractMis.mcr")
	fid.close()
	
	#Run tecplot macro
	print "*** Tecplot macro written ***"	
	print "*** Running Tecplot ***"
	os.system("rm -f data.dat")
	os.system("/gpfs/fs1/app/techplot360/bin/tec360 -b -mesa extractMis.mcr")
	'''
	#Read data and output maximum Mis
	nodeData,elementData=tecplot_reader('data.dat',1)
	print '*********************'
	maxVal=np.max( np.array(nodeData)[:,1] )
	print 'Maximum Mis at slice:',maxVal

	#Define linked list and indexes
	linkedList,listIndexes=defineLinkedList(nodeData,elementData)

	#Search list for index matching maximum Mis
	maxVal_indx=searchLinkedList(linkedList,listIndexes,maxVal)

	#Find plateau Mach number
	plateau_Mach=findPlateauMach(linkedList,maxVal_indx)
	print 'Average plateau Mis at slice:',plateau_Mach

	#Write Mis values to output file
	fid=open("crosswindMis.dat", "w") 
	fid.write(str(maxVal)+'\n')
	fid.write(str(plateau_Mach)+'\n')
	fid.close()

if __name__ == '__main__':
	main()