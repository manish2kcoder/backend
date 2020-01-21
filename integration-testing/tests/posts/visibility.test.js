/* eslint-env jest */

const path = require('path')
const uuidv4 = require('uuid/v4')

const cognito = require('../../utils/cognito.js')
const misc = require('../../utils/misc.js')
const schema = require('../../utils/schema.js')

const contentType = 'image/jpeg'
const filePath = path.join(__dirname, '..', '..', 'fixtures', 'grant.jpg')

const loginCache = new cognito.AppSyncLoginCache()

beforeAll(async () => {
  loginCache.addCleanLogin(await cognito.getAppSyncLogin())
  loginCache.addCleanLogin(await cognito.getAppSyncLogin())
  loginCache.addCleanLogin(await cognito.getAppSyncLogin())
})

beforeEach(async () => await loginCache.clean())
afterAll(async () => await loginCache.clean())


test('Visiblity of getPost(), getPosts(), getMediaObjects() for a public user', async () => {
  const [ourClient, ourUserId] = await loginCache.getCleanLogin()

  // a user that follows us
  const [followerClient] = await loginCache.getCleanLogin()
  let resp = await followerClient.mutate({mutation: schema.followUser, variables: {userId: ourUserId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['followUser']['followedStatus']).toBe('FOLLOWING')

  // some rando off the internet
  const [randoClient] = await loginCache.getCleanLogin()

  // we add a media post, give s3 trigger a second to fire
  const [postId, mediaId] = [uuidv4(), uuidv4()]
  resp = await ourClient.mutate({mutation: schema.addOneMediaPost, variables: {postId, mediaId, mediaType: 'IMAGE'}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['addPost']['postId']).toBe(postId)
  expect(resp['data']['addPost']['mediaObjects'][0]['mediaId']).toBe(mediaId)
  const uploadUrl = resp['data']['addPost']['mediaObjects'][0]['uploadUrl']

  // test we can see the uploadUrl if we ask for the incomplete mediaObjects directly
  resp = await ourClient.query({
    query: schema.getMediaObjects,
    variables: {userId: ourUserId, mediaStatus: 'AWAITING_UPLOAD'},
  })
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getMediaObjects']['items']).toHaveLength(1)
  expect(resp['data']['getMediaObjects']['items'][0]['mediaId']).toBe(mediaId)
  expect(resp['data']['getMediaObjects']['items'][0]['mediaStatus']).toBe('AWAITING_UPLOAD')
  expect(resp['data']['getMediaObjects']['items'][0]['uploadUrl']).not.toBeNull()

  // upload the media, give S3 trigger a second to fire
  await misc.uploadMedia(filePath, contentType, uploadUrl)
  await misc.sleep(2000)

  // we should see the post
  resp = await ourClient.query({query: schema.getPosts})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getPosts']['items']).toEqual([expect.objectContaining({postId})])
  resp = await ourClient.query({query: schema.getPosts, variables: {userId: ourUserId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getPosts']['items']).toEqual([expect.objectContaining({postId})])
  resp = await ourClient.query({query: schema.getPost, variables: {postId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getPost']).toMatchObject({postId})

  // we should see the media object
  resp = await ourClient.query({query: schema.getMediaObjects})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getMediaObjects']['items']).toEqual([expect.objectContaining({mediaId})])
  resp = await ourClient.query({query: schema.getMediaObjects, variables: {userId: ourUserId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getMediaObjects']['items']).toEqual([expect.objectContaining({mediaId})])

  // our follower should be able to see the post
  resp = await followerClient.query({query: schema.getPosts, variables: {userId: ourUserId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getPosts']['items']).toEqual([expect.objectContaining({postId})])
  resp = await followerClient.query({query: schema.getPost, variables: {postId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getPost']).toMatchObject({postId})

  // our follower should be able to see the media
  resp = await followerClient.query({query: schema.getMediaObjects, variables: {userId: ourUserId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getMediaObjects']['items']).toEqual([expect.objectContaining({mediaId})])

  // the rando off the internet should be able to see the post
  resp = await randoClient.query({query: schema.getPosts, variables: {userId: ourUserId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getPosts']['items']).toEqual([expect.objectContaining({postId})])
  resp = await randoClient.query({query: schema.getPost, variables: {postId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getPost']).toMatchObject({postId})

  // the rando off the internet should be able to see the media object
  resp = await randoClient.query({query: schema.getMediaObjects, variables: {userId: ourUserId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getMediaObjects']['items']).toEqual([expect.objectContaining({mediaId})])
})


test('Visiblity of getPost(), getPosts(), getMediaObjects() for a private user', async () => {
  // our user, set to private
  const [ourClient, ourUserId] = await loginCache.getCleanLogin()
  let resp = await ourClient.mutate({mutation: schema.setUserPrivacyStatus, variables: {privacyStatus: 'PRIVATE'}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['setUserDetails']['privacyStatus']).toBe('PRIVATE')

  // some rando off the internet
  const [randoClient] = await loginCache.getCleanLogin()

  // we add a media post, give s3 trigger a second to fire
  const [postId, mediaId] = [uuidv4(), uuidv4()]
  resp = await ourClient.mutate({mutation: schema.addOneMediaPost, variables: {postId, mediaId, mediaType: 'IMAGE'}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['addPost']['postId']).toBe(postId)
  expect(resp['data']['addPost']['mediaObjects'][0]['mediaId']).toBe(mediaId)
  const uploadUrl = resp['data']['addPost']['mediaObjects'][0]['uploadUrl']
  await misc.uploadMedia(filePath, contentType, uploadUrl)
  await misc.sleep(3000)

  // we should see the post
  resp = await ourClient.query({query: schema.getPosts})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getPosts']['items']).toEqual([expect.objectContaining({postId})])
  resp = await ourClient.query({query: schema.getPosts, variables: {userId: ourUserId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getPosts']['items']).toEqual([expect.objectContaining({postId})])
  resp = await ourClient.query({query: schema.getPost, variables: {postId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getPost']).toMatchObject({postId})

  // we should see the media object
  resp = await ourClient.query({query: schema.getMediaObjects})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getMediaObjects']['items']).toEqual([expect.objectContaining({mediaId})])
  resp = await ourClient.query({query: schema.getMediaObjects, variables: {userId: ourUserId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getMediaObjects']['items']).toEqual([expect.objectContaining({mediaId})])

  // the rando off the internet should *not* be able to see the post
  resp = await randoClient.query({query: schema.getPosts, variables: {userId: ourUserId}})
  expect(resp['data']).toBeNull()
  expect(resp['errors'].length).not.toBe(0)
  resp = await randoClient.query({query: schema.getPost, variables: {postId}})
  expect(resp['data']['getPost']).toBeNull()

  // the rando off the internet should *not* be able to see the media object
  resp = await randoClient.query({query: schema.getMediaObjects, variables: {userId: ourUserId}})
  expect(resp['data']).toBeNull()
  expect(resp['errors'].length).not.toBe(0)
})


test('Visiblity of getPost(), getPosts(), getMediaObjects() for the follow stages user', async () => {
  // our user, set to private
  const [ourClient, ourUserId] = await loginCache.getCleanLogin()
  let resp = await ourClient.mutate({mutation: schema.setUserPrivacyStatus, variables: {privacyStatus: 'PRIVATE'}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['setUserDetails']['privacyStatus']).toBe('PRIVATE')

  // a user will follows us
  const [followerClient, followerUserId] = await loginCache.getCleanLogin()

  // we add a media post, give s3 trigger a second to fire
  const [postId, mediaId] = [uuidv4(), uuidv4()]
  resp = await ourClient.mutate({mutation: schema.addOneMediaPost, variables: {postId, mediaId, mediaType: 'IMAGE'}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['addPost']['postId']).toBe(postId)
  expect(resp['data']['addPost']['mediaObjects'][0]['mediaId']).toBe(mediaId)
  const uploadUrl = resp['data']['addPost']['mediaObjects'][0]['uploadUrl']
  await misc.uploadMedia(filePath, contentType, uploadUrl)
  await misc.sleep(2000)

  // request to follow, should *not* be able to see post or mediaObject
  resp = await followerClient.mutate({mutation: schema.followUser, variables: {userId: ourUserId}})
  expect(resp['errors']).toBeUndefined()
  resp = await followerClient.query({query: schema.getPosts, variables: {userId: ourUserId}})
  expect(resp['data']).toBeNull()
  expect(resp['errors'].length).not.toBe(0)
  resp = await followerClient.query({query: schema.getPost, variables: {postId}})
  expect(resp['data']['getPost']).toBeNull()
  resp = await followerClient.query({query: schema.getMediaObjects, variables: {userId: ourUserId}})
  expect(resp['data']).toBeNull()
  expect(resp['errors'].length).not.toBe(0)

  // deny the follow request, should *not* be able to see post or mediaObject
  resp = await ourClient.mutate({mutation: schema.denyFollowerUser, variables: {userId: followerUserId}})
  expect(resp['errors']).toBeUndefined()
  resp = await followerClient.query({query: schema.getPosts, variables: {userId: ourUserId}})
  expect(resp['data']).toBeNull()
  expect(resp['errors'].length).not.toBe(0)
  resp = await followerClient.query({query: schema.getPost, variables: {postId}})
  expect(resp['data']['getPost']).toBeNull()
  resp = await followerClient.query({query: schema.getMediaObjects, variables: {userId: ourUserId}})
  expect(resp['data']).toBeNull()
  expect(resp['errors'].length).not.toBe(0)

  // accept the follow request, should be able to see post and mediaObject
  resp = await ourClient.mutate({mutation: schema.acceptFollowerUser, variables: {userId: followerUserId}})
  expect(resp['errors']).toBeUndefined()
  resp = await followerClient.query({query: schema.getPosts, variables: {userId: ourUserId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getPosts']['items']).toEqual([expect.objectContaining({postId})])
  resp = await followerClient.query({query: schema.getPost, variables: {postId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getPost']).toMatchObject({postId})
  resp = await followerClient.query({query: schema.getMediaObjects, variables: {userId: ourUserId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getMediaObjects']['items']).toEqual([expect.objectContaining({mediaId})])
})


test('GetPost that does not exist', async () => {
  const [ourClient] = await loginCache.getCleanLogin()

  const postId = uuidv4()
  const resp = await ourClient.query({query: schema.getPost, variables: {postId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getPost']).toBeNull()
})


test('Post.viewedBy only visible to post owner', async () => {
  const [ourClient, ourUserId] = await loginCache.getCleanLogin()
  const [theirClient] = await loginCache.getCleanLogin()

  // we add a post
  const postId = uuidv4()
  let resp = await ourClient.mutate({mutation: schema.addTextOnlyPost, variables: {postId, text: 'lore ipsum'}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['addPost']['postId']).toBe(postId)

  // verify we can see the viewedBy list (and it's empty)
  resp = await ourClient.query({query: schema.getPostViewedBy, variables: {postId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['getPost']['viewedBy']['items']).toHaveLength(0)

  // verify they cannot see the viewedBy list
  resp = await theirClient.query({query: schema.getPostViewedBy, variables: {postId}})
  expect(resp['errors'].length).toBe(1)
  expect(resp['data']['getPost']['viewedBy']).toBeNull()

  // they follow us
  resp = await theirClient.mutate({mutation: schema.followUser, variables: {userId: ourUserId}})
  expect(resp['errors']).toBeUndefined()
  expect(resp['data']['followUser']['followedStatus']).toBe('FOLLOWING')

  // verify they cannot see the viewedBy list
  resp = await theirClient.query({query: schema.getPostViewedBy, variables: {postId}})
  expect(resp['errors'].length).toBe(1)
  expect(resp['data']['getPost']['viewedBy']).toBeNull()
})
