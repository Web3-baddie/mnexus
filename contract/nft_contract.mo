// Import necessary modules
import Nat "mo:base/Nat";
import Principal "mo:base/Principal";
import Array "mo:base/Array";

// Define the NFT data structure
type NFT = {
    id: Nat;                // Unique ID for the NFT
    owner: Principal;       // Owner of the NFT
    metadata: Text;         // Metadata associated with the NFT (e.g., name, description, image)
};

// Define the NFT contract actor
actor class NFTContract() = this {

    // Storage for NFTs
    private stable var nfts: [NFT] = [];

    // Function to mint a new NFT
    public func mintNFT(owner: Principal, metadata: Text): Nat {
        let nftId = Nat.fromInt(Array.size(nfts));  // Use the current array size as the NFT ID
        let newNFT: NFT = {
            id = nftId;
            owner = owner;
            metadata = metadata;
        };
        nfts := Array.append(nfts, [newNFT]);  // Add new NFT to the list
        return nftId;  // Return the NFT ID
    };

    // Function to transfer an NFT from one owner to another
    public func transferNFT(nftId: Nat, from: Principal, to: Principal): async Text {
        let nftIndex = Array.findIndex<NFT>(nfts, func (nft) { nft.id == nftId });

        switch (nftIndex) {
            case (null) {
                return "NFT not found";
            };
            case (?index) {
                if (nfts[index].owner != from) {
                    return "You are not the owner of this NFT";
                };
                nfts[index].owner := to;
                return "Transfer successful";
            };
        };
    };

    // Function to view the details of an NFT
    public func getNFT(nftId: Nat): async ?NFT {
        let nftIndex = Array.findIndex<NFT>(nfts, func (nft) { nft.id == nftId });
        switch (nftIndex) {
            case (null) {
                return null;  // NFT not found
            };
            case (?index) {
                return ?nfts[index];
            };
        };
    };

    // Function to get all NFTs owned by a principal
    public func getNFTsByOwner(owner: Principal): async [NFT] {
        return Array.filter<NFT>(nfts, func (nft) { nft.owner == owner });
    };
};
