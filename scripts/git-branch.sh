#!/bin/bash
# --------------------------------------------------------------------------------------------------
# Creates a git branch of the given name, pushing to GitHub, et cetera, and checkout.

# Usage: git-branch.sh your-branch-name
# Echos the exact commands it is issue as it does it.
# --------------------------------------------------------------------------------------------------
 
if [ $# != 1 ] ; then
    echo "usage: gitbanch new-branch-name"
    exit 1
fi
 
BRANCH=$1
 
echo Creating git branch: ${BRANCH} ...
 
echo \> git branch ${BRANCH}
     git branch ${BRANCH}
 
if [ $? != 0 ] ; then
    echo "gitbranch: error - did not create new branch: ${BRANCH}"
    exit 2
fi
 
echo \> git checkout ${BRANCH}
     git checkout ${BRANCH}
 
if [ $? != 0 ] ; then
    echo "gitbranch: error - did not create new branch: ${BRANCH}"
    exit 3
fi
 
echo \> git push --set-upstream origin ${BRANCH}
     git push --set-upstream origin ${BRANCH}
 
if [ $? != 0 ] ; then
    echo "gitbranch: error - did not create new branch: ${BRANCH}"
    exit 4
fi
 
exit 0
