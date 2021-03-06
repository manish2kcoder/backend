const cognito = require('../../utils/cognito')
const {mutations, queries} = require('../../schema')
const misc = require('../../utils/misc')

const loginCache = new cognito.AppSyncLoginCache()
jest.retryTimes(2)

beforeAll(async () => {
  loginCache.addCleanLogin(await cognito.getAppSyncLogin())
  loginCache.addCleanLogin(await cognito.getAppSyncLogin())
})

beforeEach(async () => await loginCache.clean())
afterAll(async () => await loginCache.reset())

test('hideFollowCounts hides follow counts and followe[r|d]Users lists', async () => {
  const {client: ourClient, userId: ourUserId} = await loginCache.getCleanLogin()
  const {client: theirClient, userId: theirUserId} = await loginCache.getCleanLogin()

  // verify defaults
  let resp = await ourClient.query({query: queries.self})
  expect(resp.data.self.followCountsHidden).toBe(false)
  expect(resp.data.self.followerCount).toBe(0)
  expect(resp.data.self.followersCount).toBe(0)
  expect(resp.data.self.followedCount).toBe(0)
  expect(resp.data.self.followedsCount).toBe(0)
  resp = await ourClient.query({query: queries.ourFollowerUsers})
  expect(resp.data.self.followerUsers.items).toHaveLength(0)
  resp = await ourClient.query({query: queries.ourFollowedUsers})
  expect(resp.data.self.followedUsers.items).toHaveLength(0)

  // they follow us, we follow them
  resp = await ourClient.mutate({mutation: mutations.followUser, variables: {userId: theirUserId}})
  resp = await theirClient.mutate({mutation: mutations.followUser, variables: {userId: ourUserId}})

  // check our followCountsHidden state, and our follow counts, other user can't see our setting
  await misc.sleep(1000) // dynamo
  resp = await theirClient.query({query: queries.user, variables: {userId: ourUserId}})
  expect(resp.data.user.followCountsHidden).toBeNull()
  expect(resp.data.user.followerCount).toBe(1)
  expect(resp.data.user.followersCount).toBe(1)
  expect(resp.data.user.followedCount).toBe(1)
  expect(resp.data.user.followedsCount).toBe(1)
  resp = await theirClient.query({query: queries.followerUsers, variables: {userId: ourUserId}})
  expect(resp.data.user.followerUsers.items).toHaveLength(1)
  expect(resp.data.user.followerUsers.items[0].userId).toBe(theirUserId)
  resp = await theirClient.query({query: queries.followedUsers, variables: {userId: ourUserId}})
  expect(resp.data.user.followedUsers.items).toHaveLength(1)
  expect(resp.data.user.followedUsers.items[0].userId).toBe(theirUserId)

  // hide our follow counts
  resp = await ourClient.mutate({mutation: mutations.setUserFollowCountsHidden, variables: {value: true}})
  expect(resp.data.setUserDetails.followCountsHidden).toBe(true)

  // verify those counts are no longer visible by the other user
  resp = await theirClient.query({query: queries.user, variables: {userId: ourUserId}})
  expect(resp.data.user.followCountsHidden).toBeNull()
  expect(resp.data.user.followerCount).toBeNull()
  expect(resp.data.user.followersCount).toBeNull()
  expect(resp.data.user.followedCount).toBeNull()
  expect(resp.data.user.followedsCount).toBeNull()
  resp = await theirClient.query({query: queries.followerUsers, variables: {userId: ourUserId}})
  expect(resp.data.user.followerUsers).toBeNull()
  resp = await theirClient.query({query: queries.followedUsers, variables: {userId: ourUserId}})
  expect(resp.data.user.followedUsers).toBeNull()

  // verify we can still see our own counts
  // TODO: should we be able to see this? Or is this a hide-it-from-yourself setting?
  resp = await ourClient.query({query: queries.self})
  expect(resp.data.self.followCountsHidden).toBe(true)
  expect(resp.data.self.followerCount).toBe(1)
  expect(resp.data.self.followersCount).toBe(1)
  expect(resp.data.self.followedCount).toBe(1)
  expect(resp.data.self.followedsCount).toBe(1)
  resp = await ourClient.query({query: queries.ourFollowerUsers})
  expect(resp.data.self.followerUsers.items).toHaveLength(1)
  expect(resp.data.self.followerUsers.items[0].userId).toBe(theirUserId)
  resp = await ourClient.query({query: queries.ourFollowedUsers})
  expect(resp.data.self.followedUsers.items).toHaveLength(1)
  expect(resp.data.self.followedUsers.items[0].userId).toBe(theirUserId)

  // reveal our follow counts
  resp = await ourClient.mutate({mutation: mutations.setUserFollowCountsHidden, variables: {value: false}})
  expect(resp.data.setUserDetails.followCountsHidden).toBe(false)

  // verify the other user can again see those counts
  resp = await theirClient.query({query: queries.user, variables: {userId: ourUserId}})
  expect(resp.data.user.followCountsHidden).toBeNull()
  expect(resp.data.user.followerCount).toBe(1)
  expect(resp.data.user.followersCount).toBe(1)
  expect(resp.data.user.followedCount).toBe(1)
  expect(resp.data.user.followedsCount).toBe(1)
  resp = await theirClient.query({query: queries.followerUsers, variables: {userId: ourUserId}})
  expect(resp.data.user.followerUsers.items).toHaveLength(1)
  expect(resp.data.user.followerUsers.items[0].userId).toBe(theirUserId)
  resp = await theirClient.query({query: queries.followedUsers, variables: {userId: ourUserId}})
  expect(resp.data.user.followedUsers.items).toHaveLength(1)
  expect(resp.data.user.followedUsers.items[0].userId).toBe(theirUserId)
})
