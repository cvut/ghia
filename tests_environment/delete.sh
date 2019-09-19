#!/usr/bin/env bash

if [[ -z "${GITHUB_USER}" ]]; then
  echo "Set environment variable GITHUB_USER"
  exit 1
fi
if [[ -z "${GITHUB_TOKEN}" ]]; then
  echo "Set environment variable GITHUB_TOKEN"
  exit 1
fi

GH_ORG="MI-PYT-ghia"
REPO=${GH_ORG}/${GITHUB_USER}

echo "HTTP DELETE https://api.github.com/repos/${REPO}"
curl --header "Authorization: token ${GITHUB_TOKEN}" -X DELETE https://api.github.com/repos/${REPO}
