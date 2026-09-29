export default class ApiUsagePlugin {
  async onload() {
    try {
      this.ctx.log.info("apimon loaded（API 用量：余额/消耗/缓存命中）");
    } catch (_) {}
  }
}
