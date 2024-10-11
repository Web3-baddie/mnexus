import Web3 from 'web3';

// Use the correct network URL for Sepolia test network
const ethNetwork = 'https://sepolia.infura.io/v3/2a195169b77c4532a9660754f9d15905';
const networks = {
  eth: new Web3(ethNetwork)
};

// Function to check the balance
const checkBalance = async (network, address) => {
  try {
    const balance = await networks[network].eth.getBalance(address);
    return networks[network].utils.fromWei(balance, 'ether');  // Return only the balance
  } catch (error) {
    throw new Error(`Error fetching balance for ${network}: ${error.message}`);
  }
};

// Function to send Ethereum
const sendEthereum = async (network, fromAddress, privateKey, toAddress, amount) => {
  try {
    const nonce = await networks[network].eth.getTransactionCount(fromAddress, 'latest'); // Get latest nonce

    // Estimate gas limit
    const gasLimit = await networks[network].eth.estimateGas({
      from: fromAddress,
      to: toAddress,
      value: networks[network].utils.toWei(amount, 'ether'),
    });

    // Fetch current gas price
    const gasPrice = await networks[network].eth.getGasPrice();

    const transaction = {
      from: fromAddress,
      to: toAddress,
      value: networks[network].utils.toWei(amount, 'ether'),
      gas: gasLimit, // Use estimated gas limit
      gasPrice: gasPrice, // Use fetched gas price
      nonce: nonce,
    };

    // Sign the transaction
    const signedTransaction = await networks[network].eth.accounts.signTransaction(transaction, privateKey);
    
    // Send the transaction
    const receipt = await networks[network].eth.sendSignedTransaction(signedTransaction.rawTransaction);
    return `Transaction successful with hash: ${receipt.transactionHash}`;  // Return transaction hash
  } catch (error) {
    throw new Error(`Error sending Ethereum: ${error.message}`);
  }
};

// Main function to handle command line execution
const main = async () => {
  const [action, network, ...args] = process.argv.slice(2); // Action can be 'check' or 'send'

  if (action === 'check') {
    const [address] = args;
    if (!networks[network]) {
      console.error('Invalid network. Choose "eth".');
      process.exit(1);
    }
    if (!networks[network].utils.isAddress(address)) {
      console.error('Invalid address provided.');
      process.exit(1);
    }
    
    const balance = await checkBalance(network, address);
    console.log(`Balance: ${balance} ETH`);  // Output only the balance

  } else if (action === 'send') {
    const [fromAddress, privateKey, toAddress, amount] = args;
    if (!networks[network]) {
      console.error('Invalid network. Choose "eth".');
      process.exit(1);
    }
    if (!networks[network].utils.isAddress(fromAddress) || !networks[network].utils.isAddress(toAddress)) {
      console.error('Invalid address provided.');
      process.exit(1);
    }

    try {
      const transactionHash = await sendEthereum(network, fromAddress, privateKey, toAddress, amount);
      console.log(transactionHash);  // Output the transaction hash on success
    } catch (error) {
      console.error(error.message);
    }
  } else {
    console.error('Invalid action. Use "check" to check balance or "send" to send Ethereum.');
    process.exit(1);
  }
};

// Run the main function directly
main().catch(error => {
  console.error(error);
  process.exit(1);
});
