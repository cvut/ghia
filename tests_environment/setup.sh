#!/usr/bin/env bash

# GITHUB_USER
# GITHUB_TOKEN
# Must be member of GHIA
# Requires git and hub
set -e

if [[ -z "${GITHUB_USER}" ]]; then
  echo "Set environment variable GH_USER"
  exit 1
fi
if [[ -z "${GITHUB_TOKEN}" ]]; then
  echo "Set environment variable GH_TOKEN"
  exit 1
fi

GITHUB_ORG="MI-PYT-ghia"
REPO=${GITHUB_ORG}/${GITHUB_USER}

# Create repo
mkdir -p "${GITHUB_USER}"
cd "${GITHUB_USER}" || exit
git init
git commit --allow-empty -m"Initial commit"
hub create "${REPO}"
git push -u origin master

# Issue 1
hub issue create -F ../issues/issue.001.txt
# Issue 2
hub issue create -F ../issues/issue.002.txt
# Issue 3
hub issue create -F ../issues/issue.003.txt -l"Frontend" -l"Bug"
# Issue 4
hub issue create -F ../issues/issue.004.txt
# Issue 5
hub issue create -F ../issues/issue.005.txt  -l"assign-anna" -a"ghia-anna"
# Issue 6
hub issue create -F ../issues/issue.006.txt
# Issue 7
hub issue create -F ../issues/issue.007.txt -l"assign-anna" -l"assign-john" -a"ghia-anna" -a"ghia-john"
# Issue 8
hub issue create -F ../issues/issue.008.txt -l"assign-anna" -l"assign-peter" -a"ghia-anna" -a"ghia-peter"
# Issue 9
hub issue create -F ../issues/issue.009.txt
# Issue 10
hub issue create -F ../issues/dummy.txt -l"Need assignment"
# Issue 11
hub issue create -F ../issues/issue.011.txt -l"Python" -l"regex" -l"matching"
# Issue 12
hub issue create -F ../issues/dummy.txt -l"Need assignment"
# Issue 13
hub issue create -F ../issues/issue.013.txt
# Issue 14
hub issue create -F ../issues/dummy.txt -l"Need assignment"
# Issue 15
hub issue create -F ../issues/issue.015.txt -l"Cython"
# Issue 16
hub issue create -F ../issues/dummy.txt -l"Need assignment"
# Issue 17
hub issue create -F ../issues/issue.017.txt
# Issue 18-20
hub issue create -F ../issues/dummy.txt -l"Need assignment"
hub issue create -F ../issues/dummy.txt -l"Need assignment"
hub issue create -F ../issues/dummy.txt -l"Need assignment"
# Issue 21
hub issue create -F ../issues/issue.021.txt
# Issue 22-23
hub issue create -F ../issues/dummy.txt -l"Need assignment"
hub issue create -F ../issues/dummy.txt -l"Need assignment"
# Issue 24
hub issue create -F ../issues/issue.024.txt -l"assign-anna" -a"ghia-anna"
# Issue 25-26
hub issue create -F ../issues/dummy.txt -l"Need assignment"
hub issue create -F ../issues/dummy.txt -l"Need assignment"
# Issue 27
hub issue create -F ../issues/issue.027.txt
# Issue 28-32
for _ in {28..32}; do
    hub issue create -F ../issues/dummy.txt -l"Need assignment"
done
# Issue 33
hub issue create -F ../issues/issue.033.txt -l"question" -l"Frontend" -l"Improvement"
# Issue 34-45
for _ in {34..45}; do
    hub issue create -F ../issues/dummy.txt -l"Need assignment"
done
# Issue 46
hub issue create -F ../issues/issue.046.txt -l"Network"
# Issue 47
hub issue create -F ../issues/issue.047.txt -l"Develop" -l"Setup"
# Issue 48
hub issue create -F ../issues/issue.048.txt
# Issue 49
hub issue create -F ../issues/dummy.txt -l"Need assignment"
# Issue 50
hub issue create -F ../issues/issue.050.txt -l"Need assignment"
hub api -XPATCH repos/${REPO}/issues/50 -f state=closed
# Issue 51
hub issue create -F ../issues/issue.051.txt
hub api -XPATCH repos/${REPO}/issues/51 -f state=closed
# Issue 52
hub issue create -F ../issues/issue.052.txt -l"Bug" -l"Website" -a"ghia-anna"
hub api -XPATCH repos/${REPO}/issues/52 -f state=closed
# Issue 53
hub issue create -F ../issues/issue.053.txt -l"Python"
hub api -XPATCH repos/${REPO}/issues/53 -f state=closed
# Issue 54
hub issue create -F ../issues/issue.054.txt
hub api -XPATCH repos/${REPO}/issues/54 -f state=closed
# Issue 55
hub issue create -F ../issues/issue.055.txt -l"MySQL" -l"question" -a"ghia-peter"
hub api -XPATCH repos/${REPO}/issues/55 -f state=closed
# Issue 56
hub issue create -F ../issues/issue.056.txt -l"I18N"
hub api -XPATCH repos/${REPO}/issues/56 -f state=closed
# Issue 57
hub issue create -F ../issues/issue.057.txt
hub api -XPATCH repos/${REPO}/issues/57 -f state=closed
# Issue 58-59
hub issue create -F ../issues/dummy.txt -l"Need assignment"
hub issue create -F ../issues/dummy.txt -l"Need assignment"
# Issue 60
hub issue create -F ../issues/issue.060.txt -l"Need assignment"
# Issue 61-66
for _ in {61..66}; do
    hub issue create -F ../issues/dummy.txt -l"Need assignment"
done
# Issue 67
hub issue create -F ../issues/issue.067.txt -l"Need assignment" -l"Urgent"
# Issue 68-75
for _ in {68..75}; do
    hub issue create -F ../issues/dummy.txt -l"Need assignment"
done
# Issue 76
hub issue create -F ../issues/issue.076.txt -l"Backend" -l"Need assignment" -l"Bug"
# Issue 77-82
for _ in {77..82}; do
    hub issue create -F ../issues/dummy.txt -l"Need assignment"
done
# Issue 83
hub issue create -F ../issues/issue.083.txt -l"Docs" -l"Need assignment"
# Issue 84-95
for _ in {84..95}; do
    hub issue create -F ../issues/dummy.txt -l"Need assignment"
done
# Issue 96
hub issue create -F ../issues/issue.096.txt -l"Lang"
# Issue 97-109
for _ in {97..109}; do
    hub issue create -F ../issues/dummy.txt -l"Need assignment"
done
# Issue 110
hub issue create -F ../issues/issue.110.txt
# Issue 111
hub issue create -F ../issues/issue.111.txt
# Issue 112
hub issue create -F ../issues/issue.112.txt -l"Frontend"
# Issue 113
hub issue create -F ../issues/issue.113.txt -l"Jython" -l"Self-education"
# Issue 114
hub issue create -F ../issues/issue.114.txt
# Issue 115
hub issue create -F ../issues/issue.115.txt -l"Need assignment"
# Issue 116
hub issue create -F ../issues/issue.116.txt -l"DB Migration" -l"question"
# Issue 117
hub issue create -F ../issues/issue.117.txt -l"assign-anna" -a"ghia-anna"
# Issue 118
hub issue create -F ../issues/issue.118.txt -l"assign-peter" -a"ghia-peter"
# Issue 119
hub issue create -F ../issues/issue.119.txt
# Issue 120
hub issue create -F ../issues/dummy.txt -l"Need assignment"

cd ..
rm -rf "${GITHUB_USER}"
