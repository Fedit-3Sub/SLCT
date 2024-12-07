const puppeteer = require('puppeteer');

module.exports = {
  async scrapeData(url) {
    console.log(`Starting scraping for URL: ${url}`);

    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();

    try {
      await page.goto(url, { waitUntil: 'networkidle2' });
      console.log('Page loaded successfully');

      const buttonSelector = '.aside-list button';
      await page.waitForSelector(buttonSelector);
      console.log('Button selector found');

      const buttons = await page.$$(buttonSelector);

      const results = [];
      for (let i = 0; i < buttons.length; i++) {
        console.log(`Clicking button ${i + 1} of ${buttons.length}`);
        await buttons[i].click();

        const detailSelector = '.new-data-model-info';
        await page.waitForSelector(detailSelector);
        console.log('Detail selector found');

        const data = await page.evaluate(() => {
          const getText = (selector) =>
            document.querySelector(selector)?.innerText.trim() || '';

          return {
            id: getText('.new-data-model-info .input-container:nth-child(1) p'),
            type: getText('.new-data-model-info .input-container:nth-child(2) p'),
            title: getText('.new-data-model-info .input-container:nth-child(3) input'),
            description: getText('.new-data-model-info .input-container:nth-child(4) input'),
            reference: getText('.new-data-model-info .editable-list-wrapper input'),
          };
        });

        console.log(`Data retrieved: ${JSON.stringify(data)}`);
        results.push(data);

        // Wait before next click
        await new Promise((resolve) => setTimeout(resolve, 500));
      }

      await browser.close();
      console.log('Browser closed');
      return results;
    } catch (error) {
      console.error('Error during scraping:', error);
      await browser.close();
      throw error;
    }
  },
};

// 단독 실행용 테스트 코드
if (require.main === module) {
  const testURL = 'http://220.124.222.90:50031/service-description-tool/object-data-model-management';

  module.exports.scrapeData(testURL)
    .then((data) => {
      console.log('Scraping completed successfully:', data);
    })
    .catch((error) => {
      console.error('Scraping failed:', error);
    });
}
