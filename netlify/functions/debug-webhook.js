exports.config = { rawBody: true };

exports.handler = async (event) => {
  return {
    statusCode: 200,
    body: JSON.stringify({
      receivedType: event.headers["content-type"],
      length: event.body.length,
      startsWith: event.body.slice(0, 50),
    }),
  };
};